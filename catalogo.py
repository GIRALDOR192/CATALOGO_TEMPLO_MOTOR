import pandas as pd
import os
import base64
from datetime import datetime
import json
import re

def convertir_imagen_a_base64(ruta_imagen):
    """Convierte cualquier imagen a base64 para incluirla en el HTML"""
    try:
        with open(ruta_imagen, "rb") as img_file:
            imagen_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Determinar el tipo MIME basado en la extensión
        extension = os.path.splitext(ruta_imagen)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml'
        }
        mime_type = mime_types.get(extension, 'image/png')
        
        return f"data:{mime_type};base64,{imagen_base64}"
    except Exception as e:
        print(f"⚠️ No se pudo cargar la imagen: {e}")
        print(f"   Ruta intentada: {ruta_imagen}")
        return None

def normalizar_texto(texto):
    """Normaliza texto para búsquedas más efectivas"""
    if not isinstance(texto, str):
        return ""
    
    # Convertir a minúsculas y eliminar acentos
    texto = texto.lower()
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n'
    }
    
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    
    # Eliminar caracteres especiales excepto espacios
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    
    return texto.strip()

def calcular_precio_con_comision(precio_base, porcentaje_comision):
    """Calcula el precio final con comisión e IVA"""
    if precio_base <= 0:
        return 0, 0, 0
    
    # Calcular comisión
    comision = precio_base * (porcentaje_comision / 100)
    
    # Calcular IVA sobre la comisión (19%)
    iva_comision = comision * 0.19
    
    # Precio total
    total = precio_base + comision + iva_comision
    
    # Redondear a múltiplos de 100
    total = round(total / 100) * 100
    
    return total, comision, iva_comision

def generar_catalogo_completo():
    # CONFIGURACIÓN DE RUTAS
    ruta_excel = r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\catalogo_completo\CATALOGO TEMPLO GARAGE.xlsm"
    hoja_excel = "MUNDIMOTOS_COMPLETO_20251206_14"
    
    # RUTAS DE IMÁGENES
    ruta_logo_templo = r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\TEMPLO GARAGE STREET.png"
    ruta_logo_tiktok = r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\LOGO TIKTOK.jpeg"
    ruta_portada = r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\iloveimg-background-removed\portada.png"
    
    archivo_salida = "catalogo_completo_final.html"
    
    print("🚀 INICIANDO GENERACIÓN DE CATÁLOGO MEJORADO...")
    print("="*70)
    
    try:
        # 1. CARGAR Y PROCESAR IMÁGENES
        print("📸 Cargando imágenes de logos y portada...")
        
        # Verificar si las imágenes existen
        for ruta, nombre in [
            (ruta_logo_templo, "Logo Templo Garage"),
            (ruta_logo_tiktok, "Logo TikTok"),
            (ruta_portada, "Portada")
        ]:
            if os.path.exists(ruta):
                print(f"   ✓ {nombre}: Encontrado")
            else:
                print(f"   ✗ {nombre}: No encontrado - Ruta: {ruta}")
        
        logo_templo_base64 = convertir_imagen_a_base64(ruta_logo_templo)
        logo_tiktok_base64 = convertir_imagen_a_base64(ruta_logo_tiktok)
        portada_base64 = convertir_imagen_a_base64(ruta_portada)
        
        # 2. CARGAR DATOS DEL EXCEL
        print("\n📊 Cargando Excel con productos...")
        print(f"   Ruta: {ruta_excel}")
        print(f"   Hoja: {hoja_excel}")
        
        try:
            # Leer el Excel para ver qué columnas tiene
            xls = pd.ExcelFile(ruta_excel)
            print(f"   Hojas disponibles: {xls.sheet_names}")
            
            if hoja_excel not in xls.sheet_names:
                print(f"   ⚠️ La hoja '{hoja_excel}' no existe. Usando la primera hoja.")
                hoja_excel = xls.sheet_names[0]
            
            # Leer todas las columnas primero para ver qué hay
            df_temp = pd.read_excel(ruta_excel, sheet_name=hoja_excel, nrows=5)
            print(f"   Columnas encontradas ({len(df_temp.columns)}): {list(df_temp.columns)}")
            
            # Definir posibles nombres de columnas
            posibles_columnas = {
                'MARCA': ['MARCA', 'Marca', 'marca', 'BRAND', 'Brand'],
                'NOMBRE': ['NOMBRE', 'Nombre', 'nombre', 'PRODUCTO', 'Producto'],
                'PRECIO': ['PRECIO MUNDIMOTOS', 'PRECIO', 'Precio', 'PRICE', 'Price'],
                'IMAGEN': ['imagen_url', 'IMAGEN_URL', 'URL_IMAGEN', 'Imagen', 'imagen'],
                'DESCRIPCION': ['DESCRIPCION', 'Descripcion', 'descripcion', 'DESCRIPTION'],
                'TIPO': ['TIPO', 'Tipo', 'tipo', 'CATEGORIA', 'Categoria']
            }
            
            # Determinar qué columnas usar
            columnas_a_usar = []
            for col_std, posibles in posibles_columnas.items():
                for posible in posibles:
                    if posible in df_temp.columns:
                        columnas_a_usar.append(posible)
                        print(f"   ✓ Usando columna: '{posible}'")
                        break
            
            if not columnas_a_usar:
                print("   ⚠️ No se encontraron columnas esperadas. Leyendo todas...")
                df = pd.read_excel(ruta_excel, sheet_name=hoja_excel)
            else:
                df = pd.read_excel(ruta_excel, sheet_name=hoja_excel, usecols=columnas_a_usar)
                
            print(f"   ✅ Excel cargado con {len(df)} filas y {len(df.columns)} columnas")
            
        except Exception as e:
            print(f"   ❌ Error leyendo Excel: {e}")
            print("   Creando datos de prueba...")
            # Crear datos de prueba
            datos_prueba = {
                'MARCA': ['Yamaha', 'Honda', 'AKT', 'Suzuki', 'Kawasaki'] * 20,
                'NOMBRE': ['Filtro de Aire Premium', 'Cadena 428 Original', 'Bujía NGK Iridium', 'Aceite 20W50 Sintético', 'Pastillas Freno Delanteras'] * 20,
                'PRECIO MUNDIMOTOS': [45000, 120000, 15000, 35000, 80000] * 20,
                'imagen_url': ['https://via.placeholder.com/400x300/FF0000/FFFFFF?text=Yamaha',
                              'https://via.placeholder.com/400x300/1a237e/FFFFFF?text=Honda',
                              'https://via.placeholder.com/400x300/25D366/FFFFFF?text=AKT',
                              'https://via.placeholder.com/400x300/FFC107/FFFFFF?text=Suzuki',
                              'https://via.placeholder.com/400x300/9C27B0/FFFFFF?text=Kawasaki'] * 20,
                'DESCRIPCION': ['Filtro de aire original para motos Yamaha', 
                               'Cadena de transmisión 428 eslabones original Honda',
                               'Bujía NGK Iridium de alto rendimiento', 
                               'Aceite sintético 20W50 1L para motos', 
                               'Pastillas de freno delanteras originales'] * 20,
                'TIPO': ['Filtro', 'Transmisión', 'Eléctrico', 'Lubricante', 'Frenos'] * 20
            }
            df = pd.DataFrame(datos_prueba)
        
        print(f"✅ {len(df)} productos cargados")
        
        # 3. PROCESAR PRODUCTOS
        productos = []
        marcas_unicas = set()
        
        print("\n🔄 Procesando productos...")
        for idx, row in df.iterrows():
            try:
                # Extraer datos con manejo seguro
                marca = str(row.get('MARCA', '')).strip()[:30] if pd.notna(row.get('MARCA', '')) else 'Genérica'
                nombre = str(row.get('NOMBRE', '')).strip()[:100] if pd.notna(row.get('NOMBRE', '')) else 'Sin nombre'
                descripcion = str(row.get('DESCRIPCION', '')).strip()[:150] if pd.notna(row.get('DESCRIPCION', '')) else 'Sin descripción'
                tipo = str(row.get('TIPO', '')).strip()[:20] if pd.notna(row.get('TIPO', '')) else 'Accesorio'
                
                # Procesar precio
                precio_raw = row.get('PRECIO MUNDIMOTOS', 0)
                precio_num = 0
                precio_str = "Consultar"
                
                if pd.notna(precio_raw):
                    try:
                        if isinstance(precio_raw, (int, float)):
                            precio_num = float(precio_raw)
                        else:
                            precio_texto = str(precio_raw).replace('$', '').replace(',', '').replace('.', '').strip()
                            if precio_texto.isdigit():
                                precio_num = float(precio_texto)
                            else:
                                precio_texto = str(precio_raw).replace('$', '').replace(',', '').strip()
                                if precio_texto.replace('.', '', 1).isdigit():
                                    precio_num = float(precio_texto)
                        
                        if precio_num > 0:
                            precio_str = f"${precio_num:,.0f}".replace(',', '.')
                    except:
                        precio_num = 0
                        precio_str = "Consultar"
                
                # Procesar imagen URL
                imagen_raw = row.get('imagen_url', '')
                if pd.isna(imagen_raw) or not isinstance(imagen_raw, str) or not imagen_raw.startswith(('http', 'https')):
                    colores = ['FF0000', '1a237e', '25D366', 'FFC107', '9C27B0']
                    color_idx = hash(marca) % len(colores)
                    color = colores[color_idx]
                    marca_sin_espacios = marca.replace(' ', '+')[:15]
                    imagen = f"https://via.placeholder.com/400x300/{color}/FFFFFF?text={marca_sin_espacios}"
                else:
                    imagen = str(imagen_raw).strip()
                
                # Calcular precios con comisiones
                comisiones = {
                    'nequi': {
                        'porcentaje': 1.5,
                        'nombre': 'Nequi/Bancolombia',
                        'total': 0,
                        'comision': 0,
                        'iva': 0
                    },
                    'tarjeta': {
                        'porcentaje': 1.99,
                        'nombre': 'Tarjetas débito/crédito',
                        'total': 0,
                        'comision': 0,
                        'iva': 0
                    },
                    'pse': {
                        'porcentaje': 2.69,
                        'nombre': 'Otros bancos (PSE)',
                        'total': 0,
                        'comision': 0,
                        'iva': 0
                    }
                }
                
                if precio_num > 0:
                    for key in comisiones:
                        total, comision, iva = calcular_precio_con_comision(
                            precio_num, 
                            comisiones[key]['porcentaje']
                        )
                        comisiones[key]['total'] = total
                        comisiones[key]['comision'] = comision
                        comisiones[key]['iva'] = iva
                
                # Crear objeto producto
                producto = {
                    'id': idx + 1,
                    'marca': marca,
                    'nombre': nombre,
                    'nombre_normalizado': normalizar_texto(nombre),
                    'marca_normalizada': normalizar_texto(marca),
                    'descripcion': descripcion,
                    'descripcion_normalizada': normalizar_texto(descripcion),
                    'precio': precio_num,
                    'precio_str': precio_str,
                    'imagen': imagen,
                    'tipo': tipo,
                    'categoria': 'motos',
                    'rating': 4.9,
                    'comentarios': 156,
                    'comisiones': comisiones
                }
                
                productos.append(producto)
                marcas_unicas.add(marca)
                
                # Mostrar progreso cada 500 productos
                if (idx + 1) % 500 == 0:
                    print(f"   📦 Procesados: {idx + 1}/{len(df)} productos")
                    
            except Exception as e:
                continue
        
        print(f"\n🎯 {len(productos)} productos procesados correctamente")
        print(f"🏷️  Marcas únicas encontradas: {len(marcas_unicas)}")
        
        # 4. PREPARAR DATOS PARA JAVASCRIPT
        print("\n💾 Preparando datos para JavaScript...")
        productos_json = json.dumps(productos, ensure_ascii=False, separators=(',', ':'))
        
        # 5. CONFIGURACIÓN DE PAGO
        link_pago_base = "https://checkout.nequi.wompi.co/l/VPOS_UD3qM7"
        whatsapp_numero = "573224832415"
        tiktok_url = "https://www.tiktok.com/@brujablanca51"
        
        # 6. GENERAR HTML COMPLETO
        print("🚀 Generando HTML optimizado...")
        
        # Preparar URLs de TikTok
        tiktok_brujablanca = "https://www.tiktok.com/@brujablanca51"
        tiktok_naturista = "https://www.tiktok.com/@naturista_venuz"
        
        # Construir el HTML
        html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Templo Garage Street & TikTok Moto Parts - Catálogo Completo</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap">
    <style>
        /* ESTILOS GLOBALES */
        :root {{
            --primary: #FF0000; /* Rojo TikTok */
            --secondary: #1a237e; /* Azul Templo Garage */
            --accent: #25D366; /* Verde WhatsApp */
            --tiktok-color: #000000; /* Negro TikTok */
            --dark: #121212;
            --light: #f8f9fa;
            --gray: #6c757d;
            --success: #28a745;
            --warning: #ffc107;
            --gradient-primary: linear-gradient(135deg, #FF0000 0%, #1a237e 100%);
            --gradient-secondary: linear-gradient(135deg, #1a237e 0%, #000000 100%);
            --gradient-protect: linear-gradient(135deg, #FF0000 0%, #FF9800 50%, #FF0000 100%);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Poppins', sans-serif;
            background: #0a0a0a;
            color: #fff;
            line-height: 1.6;
            overflow-x: hidden;
            padding-bottom: 100px; /* Espacio para botones flotantes */
        }}
        
        /* PORTADA CON IMAGEN DE FONDO */
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
        }}
        
        .portada::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('{portada_base64 if portada_base64 else "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80"}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            filter: brightness(0.3) contrast(1.2);
            z-index: 1;
        }}
        
        .portada-content {{
            position: relative;
            z-index: 2;
            max-width: 1400px;
            width: 100%;
        }}
        
        /* LOGOS DUALES */
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
            padding: 20px;
            border-radius: 20px;
            background: rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .logo-wrapper:hover {{
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(255, 0, 0, 0.3);
        }}
        
        .logo-img {{
            height: 120px;
            width: auto;
            max-width: 300px;
            object-fit: contain;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.7));
            margin-bottom: 15px;
        }}
        
        .logo-label {{
            font-size: 18px;
            font-weight: 700;
            color: white;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
            padding: 10px 25px;
            border-radius: 25px;
        }}
        
        .logo-tiktok .logo-label {{
            background: linear-gradient(135deg, rgba(255, 0, 0, 0.9) 0%, rgba(255, 20, 147, 0.9) 100%);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }}
        
        .logo-templo .logo-label {{
            background: linear-gradient(135deg, rgba(26, 35, 126, 0.9) 0%, rgba(13, 71, 161, 0.9) 100%);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }}
        
        /* TÍTULO PRINCIPAL */
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
            color: #fff;
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
        
        /* TEXTO PROTEGEMOS TODAS TUS PARTES */
        .protect-text {{
            font-size: 3rem;
            font-weight: 900;
            color: white;
            margin: 40px auto 80px auto; /* Aumentado margen inferior */
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
        
        /* BOTONES DE CATEGORÍA - SUBIDOS MÁS */
        .categoria-filtros {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 40px 0 100px 0; /* Aumentado margen inferior */
            flex-wrap: wrap;
            position: relative;
            z-index: 10;
        }}
        
        .categoria-btn {{
            padding: 18px 40px;
            border: none;
            border-radius: 15px;
            font-size: 20px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 280px;
            justify-content: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}
        
        .categoria-btn.active {{
            background: var(--gradient-primary);
            color: white;
            transform: translateY(-5px) scale(1.05);
            box-shadow: 0 15px 30px rgba(255, 0, 0, 0.4);
        }}
        
        .categoria-btn:not(.active) {{
            background: rgba(255,255,255,0.15);
            color: #fff;
            border: 2px solid rgba(255,255,255,0.25);
        }}
        
        .categoria-btn:not(.active):hover {{
            background: rgba(255,255,255,0.25);
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(255,255,255,0.2);
        }}
        
        /* BARRA DE BÚSQUEDA CON AUTOCOMPLETADO */
        .search-section {{
            background: rgba(26, 35, 126, 0.2);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 20px;
            margin: 60px auto; /* Aumentado margen superior */
            max-width: 1200px;
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            z-index: 5;
        }}
        
        .search-container {{
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            position: relative;
        }}
        
        .search-input {{
            flex: 1;
            padding: 20px 25px;
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 15px;
            font-size: 18px;
            background: rgba(0,0,0,0.5);
            color: white;
            transition: all 0.3s;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(255, 0, 0, 0.2);
        }}
        
        .search-btn {{
            background: var(--gradient-primary);
            color: white;
            border: none;
            padding: 0 40px;
            border-radius: 15px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.3s;
        }}
        
        .search-btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(255, 0, 0, 0.3);
        }}
        
        /* AUTOCOMPLETADO */
        .autocomplete-container {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.95);
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.2);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            margin-top: 5px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        
        .autocomplete-item {{
            padding: 15px 20px;
            cursor: pointer;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .autocomplete-item:hover {{
            background: rgba(255, 0, 0, 0.2);
        }}
        
        .autocomplete-item .product-name {{
            font-weight: 600;
            color: white;
            flex: 1;
        }}
        
        .autocomplete-item .product-brand {{
            font-size: 12px;
            color: var(--primary);
            background: rgba(255, 0, 0, 0.1);
            padding: 2px 8px;
            border-radius: 10px;
        }}
        
        .autocomplete-item .product-price {{
            color: var(--accent);
            font-weight: 600;
            font-size: 14px;
        }}
        
        /* FILTROS */
        .filters-row {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        
        .filter-select {{
            padding: 15px 25px;
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            background: rgba(0,0,0,0.5);
            color: white;
            font-size: 16px;
            min-width: 200px;
            cursor: pointer;
        }}
        
        /* PRODUCTOS */
        .productos-container {{
            max-width: 1400px;
            margin: 50px auto;
            padding: 0 20px;
        }}
        
        .productos-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            flex-wrap: wrap;
            gap: 20px;
        }}
        
        .productos-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 30px;
        }}
        
        .product-card {{
            background: rgba(26, 35, 126, 0.1);
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.4s;
        }}
        
        .product-card:hover {{
            transform: translateY(-10px);
            border-color: var(--primary);
            box-shadow: 0 20px 40px rgba(255, 0, 0, 0.3);
        }}
        
        .product-image {{
            width: 100%;
            height: 250px;
            object-fit: contain;
            background: rgba(0,0,0,0.3);
            padding: 20px;
        }}
        
        .product-info {{
            padding: 25px;
        }}
        
        .product-marca {{
            color: var(--primary);
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        
        .product-nombre {{
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 15px;
            color: white;
            min-height: 60px;
        }}
        
        .product-precio {{
            font-size: 28px;
            font-weight: 800;
            color: var(--primary);
            margin: 20px 0;
        }}
        
        .product-rating {{
            display: flex;
            align-items: center;
            gap: 5px;
            margin: 15px 0;
            color: var(--warning);
        }}
        
        .btn-pagar {{
            display: block;
            width: 100%;
            padding: 18px;
            background: var(--gradient-primary);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            margin-top: 15px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        
        .btn-pagar:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(255, 0, 0, 0.3);
        }}
        
        .btn-whatsapp {{
            display: block;
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, var(--accent) 0%, #128C7E 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            margin-top: 10px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        
        .btn-whatsapp:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(37, 211, 102, 0.3);
        }}
        
        /* MODAL DE PAGO - MEJORADO Y ORGANIZADO */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 2000;
            overflow-y: auto;
            padding: 20px;
        }}
        
        .modal-content {{
            background: rgba(18, 18, 18, 0.98);
            max-width: 800px;
            margin: 50px auto;
            border-radius: 25px;
            border: 2px solid var(--primary);
            overflow: hidden;
            animation: modalFadeIn 0.3s;
            box-shadow: 0 20px 50px rgba(255, 0, 0, 0.3);
        }}
        
        @keyframes modalFadeIn {{
            from {{ opacity: 0; transform: translateY(-50px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .modal-header {{
            background: var(--gradient-primary);
            padding: 25px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid rgba(255,255,255,0.1);
        }}
        
        .modal-header h2 {{
            color: white;
            font-size: 24px;
            font-weight: 700;
        }}
        
        .close-modal {{
            background: none;
            border: none;
            color: white;
            font-size: 28px;
            cursor: pointer;
            transition: transform 0.3s;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
        }}
        
        .close-modal:hover {{
            transform: rotate(90deg);
            background: rgba(255,255,255,0.1);
        }}
        
        .modal-body {{
            padding: 30px;
        }}
        
        .modal-product-info {{
            display: flex;
            gap: 30px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        
        .modal-product-image {{
            flex: 1;
            min-width: 300px;
        }}
        
        .modal-product-image img {{
            width: 100%;
            height: 300px;
            object-fit: contain;
            border-radius: 15px;
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border: 2px solid rgba(255,255,255,0.1);
        }}
        
        .modal-product-details {{
            flex: 2;
            min-width: 300px;
        }}
        
        .modal-product-details h3 {{
            font-size: 24px;
            margin-bottom: 10px;
            color: white;
            line-height: 1.3;
        }}
        
        .modal-brand {{
            color: var(--primary);
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 15px;
        }}
        
        .modal-price-section {{
            background: rgba(26, 35, 126, 0.2);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .modal-price-label {{
            color: rgba(255,255,255,0.7);
            font-size: 14px;
            margin-bottom: 5px;
        }}
        
        .modal-price {{
            font-size: 36px;
            color: var(--primary);
            font-weight: 900;
        }}
        
        /* OPCIONES DE PAGO MEJORADAS */
        .payment-options {{
            margin: 30px 0;
        }}
        
        .payment-options h3 {{
            font-size: 18px;
            margin-bottom: 20px;
            color: white;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .payment-method {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border: 2px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
            cursor: pointer;
        }}
        
        .payment-method:hover {{
            border-color: var(--primary);
            background: rgba(255, 0, 0, 0.05);
        }}
        
        .payment-method.selected {{
            border-color: var(--primary);
            background: rgba(255, 0, 0, 0.1);
            box-shadow: 0 5px 15px rgba(255, 0, 0, 0.2);
        }}
        
        .method-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .method-name {{
            font-weight: 700;
            color: white;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .method-percentage {{
            color: var(--primary);
            font-weight: 800;
            font-size: 20px;
        }}
        
        .method-details {{
            color: rgba(255,255,255,0.7);
            font-size: 14px;
            margin-bottom: 10px;
            line-height: 1.5;
        }}
        
        .method-total {{
            font-size: 20px;
            font-weight: 900;
            color: var(--accent);
            margin-top: 10px;
        }}
        
        .shipping-info {{
            background: rgba(37, 211, 102, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            border: 1px solid rgba(37, 211, 102, 0.3);
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .shipping-info i {{
            color: #25D366;
            font-size: 20px;
        }}
        
        .shipping-info span {{
            color: rgba(255,255,255,0.9);
            font-size: 14px;
        }}
        
        /* BOTONES DEL MODAL MEJORADOS */
        .modal-buttons {{
            display: flex;
            gap: 15px;
            margin-top: 30px;
            flex-wrap: wrap;
        }}
        
        .modal-btn-wompi {{
            flex: 2;
            background: var(--gradient-primary);
            color: white;
            border: none;
            padding: 20px;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: all 0.3s;
            min-width: 250px;
        }}
        
        .modal-btn-wompi:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(255, 0, 0, 0.4);
        }}
        
        .modal-btn-whatsapp {{
            flex: 1;
            background: linear-gradient(135deg, var(--accent) 0%, #128C7E 100%);
            color: white;
            border: none;
            padding: 20px;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: all 0.3s;
            min-width: 200px;
        }}
        
        .modal-btn-whatsapp:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4);
        }}
        
        /* PAGINACIÓN */
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin: 50px 0;
            flex-wrap: wrap;
        }}
        
        .pagination-btn {{
            padding: 15px 30px;
            background: rgba(255,255,255,0.1);
            border: 2px solid rgba(255,255,255,0.2);
            color: white;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        .pagination-btn:hover:not(:disabled) {{
            background: var(--gradient-primary);
            border-color: var(--primary);
            transform: translateY(-3px);
        }}
        
        .pagination-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        /* FOOTER */
        .footer {{
            background: var(--gradient-secondary);
            padding: 60px 20px 30px;
            margin-top: 80px;
        }}
        
        .footer-content {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 40px;
        }}
        
        .footer-section h3 {{
            font-size: 20px;
            margin-bottom: 20px;
            color: white;
            border-left: 4px solid var(--primary);
            padding-left: 15px;
        }}
        
        .footer-section p {{
            color: rgba(255,255,255,0.7);
            line-height: 1.8;
        }}
        
        .footer-tiktoks {{
            margin-top: 20px;
            padding: 15px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 10px;
        }}
        
        .tiktok-link {{
            display: block;
            color: #fff;
            text-decoration: none;
            padding: 10px 15px;
            margin: 8px 0;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .tiktok-link:hover {{
            background: rgba(255, 0, 0, 0.3);
            transform: translateX(5px);
        }}
        
        /* BOTONES FLOTANTES */
        .floating-buttons {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            z-index: 1000;
        }}
        
        .whatsapp-float {{
            background: linear-gradient(135deg, var(--accent) 0%, #128C7E 100%);
            color: white;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;
            text-decoration: none;
            box-shadow: 0 5px 20px rgba(37, 211, 102, 0.4);
            transition: all 0.3s;
            animation: whatsappPulse 2s infinite;
            position: relative;
        }}
        
        @keyframes whatsappPulse {{
            0% {{ box-shadow: 0 5px 20px rgba(37, 211, 102, 0.4); }}
            50% {{ box-shadow: 0 5px 30px rgba(37, 211, 102, 0.6); transform: scale(1.1); }}
            100% {{ box-shadow: 0 5px 20px rgba(37, 211, 102, 0.4); }}
        }}
        
        .tiktok-float {{
            background: linear-gradient(135deg, #000000 0%, #FF0050 100%);
            color: white;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            text-decoration: none;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.4);
            transition: all 0.3s;
            animation: tiktokPulse 2s infinite;
            position: relative;
        }}
        
        @keyframes tiktokPulse {{
            0% {{ box-shadow: 0 5px 20px rgba(0, 0, 0, 0.4); }}
            50% {{ box-shadow: 0 5px 30px rgba(255, 0, 80, 0.6); transform: scale(1.1); }}
            100% {{ box-shadow: 0 5px 20px rgba(0, 0, 0, 0.4); }}
        }}
        
        .float-tooltip {{
            position: absolute;
            right: 70px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 10px 15px;
            border-radius: 10px;
            font-size: 14px;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .whatsapp-float:hover .float-tooltip,
        .tiktok-float:hover .float-tooltip {{
            opacity: 1;
        }}
        
        .whatsapp-float:hover {{
            transform: scale(1.1);
            box-shadow: 0 10px 30px rgba(37, 211, 102, 0.6);
        }}
        
        .tiktok-float:hover {{
            transform: scale(1.1);
            box-shadow: 0 10px 30px rgba(255, 0, 80, 0.6);
        }}
        
        /* RESPONSIVE - COMPUTADORES, CELULARES, TABLETS */
        @media (max-width: 1200px) {{
            .main-title {{
                font-size: 3rem;
            }}
            
            .protect-text {{
                font-size: 2.5rem;
            }}
            
            .categoria-filtros {{
                margin-bottom: 90px;
            }}
            
            .logos-container {{
                gap: 40px;
            }}
        }}
        
        @media (max-width: 992px) {{
            .portada {{
                height: 70vh;
                min-height: 500px;
            }}
            
            .main-title {{
                font-size: 2.5rem;
            }}
            
            .protect-text {{
                font-size: 2rem;
                padding: 15px 30px;
                margin: 30px auto 70px auto;
            }}
            
            .subtitle {{
                font-size: 1.3rem;
            }}
            
            .logo-img {{
                height: 100px;
            }}
            
            .categoria-btn {{
                min-width: 250px;
                padding: 16px 35px;
                font-size: 18px;
            }}
            
            .productos-grid {{
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            }}
            
            .floating-buttons {{
                bottom: 25px;
                right: 25px;
            }}
        }}
        
        @media (max-width: 768px) {{
            .portada {{
                height: 65vh;
                min-height: 450px;
            }}
            
            .main-title {{
                font-size: 2rem;
            }}
            
            .protect-text {{
                font-size: 1.8rem;
                padding: 15px 25px;
                margin: 25px auto 60px auto;
            }}
            
            .subtitle {{
                font-size: 1.2rem;
                padding: 12px 25px;
            }}
            
            .logos-container {{
                flex-direction: column;
                gap: 30px;
            }}
            
            .categoria-filtros {{
                margin-bottom: 80px;
                gap: 15px;
            }}
            
            .categoria-btn {{
                min-width: 100%;
                padding: 15px 30px;
                font-size: 16px;
            }}
            
            .search-container {{
                flex-direction: column;
            }}
            
            .search-btn {{
                padding: 15px;
                justify-content: center;
            }}
            
            .modal-product-info {{
                flex-direction: column;
            }}
            
            .modal-buttons {{
                flex-direction: column;
            }}
            
            .modal-btn-wompi,
            .modal-btn-whatsapp {{
                width: 100%;
                min-width: auto;
            }}
            
            .floating-buttons {{
                bottom: 20px;
                right: 20px;
            }}
            
            .whatsapp-float,
            .tiktok-float {{
                width: 55px;
                height: 55px;
                font-size: 26px;
            }}
        }}
        
        @media (max-width: 576px) {{
            .portada {{
                height: 60vh;
                min-height: 400px;
            }}
            
            .main-title {{
                font-size: 1.6rem;
            }}
            
            .protect-text {{
                font-size: 1.4rem;
                padding: 12px 20px;
                margin: 20px auto 50px auto;
            }}
            
            .subtitle {{
                font-size: 1rem;
                padding: 10px 20px;
            }}
            
            .logo-img {{
                height: 80px;
            }}
            
            .logo-label {{
                font-size: 16px;
                padding: 8px 20px;
            }}
            
            .categoria-filtros {{
                margin-bottom: 70px;
            }}
            
            .search-section {{
                padding: 20px;
                margin: 40px 15px;
            }}
            
            .productos-grid {{
                grid-template-columns: 1fr;
                gap: 20px;
            }}
            
            .product-card {{
                border-radius: 15px;
            }}
            
            .modal-content {{
                margin: 20px auto;
                border-radius: 20px;
            }}
            
            .modal-header {{
                padding: 20px;
            }}
            
            .modal-body {{
                padding: 20px;
            }}
            
            .floating-buttons {{
                bottom: 15px;
                right: 15px;
                gap: 10px;
            }}
            
            .whatsapp-float,
            .tiktok-float {{
                width: 50px;
                height: 50px;
                font-size: 24px;
            }}
            
            .float-tooltip {{
                font-size: 12px;
                padding: 8px 12px;
                right: 60px;
            }}
        }}
        
        @media (max-width: 400px) {{
            .portada {{
                height: 55vh;
                min-height: 350px;
            }}
            
            .main-title {{
                font-size: 1.4rem;
            }}
            
            .protect-text {{
                font-size: 1.2rem;
                padding: 10px 15px;
            }}
            
            .categoria-btn {{
                padding: 12px 20px;
                font-size: 14px;
            }}
            
            .search-input {{
                padding: 15px 20px;
                font-size: 16px;
            }}
            
            .product-info {{
                padding: 20px;
            }}
            
            .product-precio {{
                font-size: 24px;
            }}
            
            .btn-pagar,
            .btn-whatsapp {{
                padding: 15px;
                font-size: 16px;
            }}
        }}
        
        /* Ajustes específicos para tablets en orientación vertical */
        @media (min-width: 768px) and (max-width: 992px) and (orientation: portrait) {{
            .portada {{
                height: 60vh;
            }}
            
            .categoria-filtros {{
                margin-bottom: 85px;
            }}
            
            .productos-grid {{
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            }}
        }}
        
        /* Ajustes específicos para tablets en orientación horizontal */
        @media (min-width: 992px) and (max-width: 1200px) and (orientation: landscape) {{
            .portada {{
                height: 75vh;
            }}
            
            .categoria-filtros {{
                margin-bottom: 95px;
            }}
        }}
    </style>
</head>
<body>
    <!-- PORTADA CON LOGOS DUALES -->
    <section class="portada">
        <div class="portada-content">
            <div class="logos-container">
                <div class="logo-wrapper logo-tiktok">
                    <img src="{logo_tiktok_base64 if logo_tiktok_base64 else 'https://via.placeholder.com/300x120/FF0000/FFFFFF?text=TIKTOK+LOGO'}" 
                         alt="TikTok Moto Parts" class="logo-img">
                    <div class="logo-label">@brujablanca51</div>
                </div>
                
                <div class="logo-wrapper logo-templo">
                    <img src="{logo_templo_base64 if logo_templo_base64 else 'https://via.placeholder.com/300x120/1a237e/FFFFFF?text=TEMPLO+GARAGE'}" 
                         alt="Templo Garage Street" class="logo-img">
                    <div class="logo-label">Templo Garage</div>
                </div>
            </div>
            
            <h1 class="main-title">CATÁLOGO DIGITAL PROFESIONAL</h1>
            <p class="subtitle">Repuestos originales para motos • Envíos a toda Colombia • Compra segura con múltiples métodos de pago</p>
            
            <div class="protect-text">
                PROTEGEMOS TODAS TUS PARTES
            </div>
            
            <div class="categoria-filtros">
                <button class="categoria-btn active" onclick="filtrarPorCategoria('motos')">
                    <i class="fas fa-motorcycle"></i> REPUESTOS PARA MOTOS
                </button>
                <button class="categoria-btn" onclick="filtrarPorCategoria('carros')" disabled>
                    <i class="fas fa-car"></i> REPUESTOS PARA CARROS (PRÓXIMAMENTE)
                </button>
            </div>
        </div>
    </section>

    <!-- SECCIÓN DE BÚSQUEDA CON AUTOCOMPLETADO -->
    <section class="search-section">
        <div class="search-container">
            <input type="text" id="searchInput" class="search-input" 
                   placeholder="🔍 Busca por nombre, marca, descripción... (Ej: 'filtro', 'yamaha', 'cadena')">
            <button onclick="buscarProductos()" class="search-btn">
                <i class="fas fa-search"></i> BUSCAR
            </button>
            <div id="autocompleteList" class="autocomplete-container"></div>
        </div>
        
        <div class="filters-row">
            <select id="marcaFilter" class="filter-select" onchange="aplicarFiltros()">
                <option value="">TODAS LAS MARCAS</option>
            </select>
            
            <select id="ordenFilter" class="filter-select" onchange="aplicarFiltros()">
                <option value="nombre">ORDENAR POR NOMBRE</option>
                <option value="precio_asc">PRECIO: MENOR A MAYOR</option>
                <option value="precio_desc">PRECIO: MAYOR A MENOR</option>
                <option value="marca">ORDENAR POR MARCA</option>
            </select>
            
            <button onclick="resetFiltros()" class="search-btn" style="background: var(--gradient-secondary);">
                <i class="fas fa-redo"></i> LIMPIAR FILTROS
            </button>
        </div>
        
        <div id="searchSuggestions" style="margin-top: 15px; color: rgba(255,255,255,0.7); font-size: 14px;">
            <i class="fas fa-lightbulb"></i> <strong>Búsqueda inteligente:</strong> Escribe para ver sugerencias automáticas.
        </div>
    </section>
    
    <!-- SECCIÓN DE PRODUCTOS -->
    <section class="productos-container">
        <div class="productos-header">
            <h2 id="resultadosTitle" style="font-size: 2.5rem; background: var(--gradient-primary); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                REPUESTOS DISPONIBLES
            </h2>
            <div id="productosCount" style="font-size: 1.2rem; color: #ccc;">
                Cargando {len(productos)} productos...
            </div>
        </div>
        
        <div class="productos-grid" id="productGrid">
            <!-- Los productos se cargarán aquí con JavaScript -->
        </div>
        
        <div class="pagination">
            <button onclick="cambiarPagina(-1)" id="prevPage" class="pagination-btn" disabled>
                <i class="fas fa-chevron-left"></i> ANTERIOR
            </button>
            
            <div style="padding: 15px 30px; background: rgba(255,255,255,0.1); border-radius: 12px;">
                PÁGINA <span id="currentPage" style="color: var(--primary); font-weight: 700;">1</span> 
                DE <span id="totalPages" style="color: var(--primary); font-weight: 700;">1</span>
            </div>
            
            <button onclick="cambiarPagina(1)" id="nextPage" class="pagination-btn">
                SIGUIENTE <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    </section>
    
    <!-- MODAL DE PAGO MEJORADO -->
    <div id="pagoModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>COMPRAR PRODUCTO</h2>
                <button class="close-modal" onclick="cerrarModal()">×</button>
            </div>
            <div class="modal-body">
                <div class="modal-product-info">
                    <div class="modal-product-image">
                        <img id="modalProductImage" src="" alt="">
                    </div>
                    <div class="modal-product-details">
                        <div id="modalProductBrand" class="modal-brand"></div>
                        <h3 id="modalProductName"></h3>
                        
                        <div class="modal-price-section">
                            <div class="modal-price-label">Precio base del producto:</div>
                            <div class="modal-price" id="modalProductPrice"></div>
                        </div>
                        
                        <div class="payment-options">
                            <h3><i class="fas fa-credit-card"></i> SELECCIONA MÉTODO DE PAGO</h3>
                            
                            <div class="payment-method" data-tipo="nequi" onclick="seleccionarMetodoPago('nequi')">
                                <div class="method-header">
                                    <div class="method-name">
                                        <i class="fas fa-mobile-alt"></i> Nequi / Bancolombia
                                    </div>
                                    <div class="method-percentage">1.5%</div>
                                </div>
                                <div class="method-details">Comisión: <span id="nequiComision">$0</span> + IVA 19%: <span id="nequiIva">$0</span></div>
                                <div class="method-total" id="nequiTotal">Total a pagar: $0</div>
                            </div>
                            
                            <div class="payment-method" data-tipo="tarjeta" onclick="seleccionarMetodoPago('tarjeta')">
                                <div class="method-header">
                                    <div class="method-name">
                                        <i class="fas fa-credit-card"></i> Tarjetas débito/crédito
                                    </div>
                                    <div class="method-percentage">1.99%</div>
                                </div>
                                <div class="method-details">Comisión: <span id="tarjetaComision">$0</span> + IVA 19%: <span id="tarjetaIva">$0</span></div>
                                <div class="method-total" id="tarjetaTotal">Total a pagar: $0</div>
                            </div>
                            
                            <div class="payment-method" data-tipo="pse" onclick="seleccionarMetodoPago('pse')">
                                <div class="method-header">
                                    <div class="method-name">
                                        <i class="fas fa-university"></i> Otros bancos (PSE)
                                    </div>
                                    <div class="method-percentage">2.69%</div>
                                </div>
                                <div class="method-details">Comisión: <span id="pseComision">$0</span> + IVA 19%: <span id="pseIva">$0</span></div>
                                <div class="method-total" id="pseTotal">Total a pagar: $0</div>
                            </div>
                        </div>
                        
                        <div class="shipping-info">
                            <i class="fas fa-truck"></i>
                            <span>Envío según ubicación - Valor a acordar por WhatsApp después de la compra</span>
                        </div>
                        
                        <div class="modal-buttons">
                            <a id="modalBtnWompi" class="modal-btn-wompi" target="_blank">
                                <i class="fas fa-credit-card"></i> PAGAR CON WOMPI
                            </a>
                            <button id="modalBtnWhatsApp" class="modal-btn-whatsapp" onclick="consultarWhatsApp()">
                                <i class="fab fa-whatsapp"></i> CONSULTAR
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- FOOTER -->
    <footer class="footer">
        <div class="footer-content">
            <div class="footer-section">
                <h3>Templo Garage Street</h3>
                <p>Especialistas en repuestos originales para motos con más de 10 años de experiencia en el mercado colombiano.</p>
            </div>
            
            <div class="footer-section">
                <h3>TikTok Moto Parts</h3>
                <p>Tu tienda digital de confianza para repuestos y accesorios de motos.</p>
                <div class="footer-tiktoks">
                    <p style="color: #fff; font-weight: 700; margin-bottom: 10px;">Síguenos en TikTok:</p>
                    <a href="{tiktok_brujablanca}" target="_blank" class="tiktok-link">
                        <i class="fab fa-tiktok"></i> @brujablanca51
                    </a>
                    <a href="{tiktok_naturista}" target="_blank" class="tiktok-link">
                        <i class="fab fa-tiktok"></i> @naturista_venuz
                    </a>
                </div>
            </div>
            
            <div class="footer-section">
                <h3>Contacto</h3>
                <p><i class="fab fa-whatsapp"></i> WhatsApp: +57 322 4832415</p>
                <p><i class="fas fa-clock"></i> Horario: Lunes a Viernes 8am - 6pm</p>
                <p><i class="fas fa-truck"></i> Envíos a todo Colombia</p>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.5);">
            <p>© {datetime.now().year} Templo Garage Street & TikTok Moto Parts - Catálogo generado automáticamente</p>
            <p>Todos los precios incluyen IVA. Catálogo actualizado al {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
    </footer>
    
    <!-- BOTONES FLOTANTES -->
    <div class="floating-buttons">
        <a href="https://wa.me/{whatsapp_numero}" target="_blank" class="whatsapp-float">
            <i class="fab fa-whatsapp"></i>
            <div class="float-tooltip">¿Necesitas ayuda? ¡Escríbenos!</div>
        </a>
        <a href="{tiktok_url}" target="_blank" class="tiktok-float">
            <i class="fab fa-tiktok"></i>
            <div class="float-tooltip">Síguenos en TikTok</div>
        </a>
    </div>
    
    <!-- SCRIPT DE PRODUCTOS -->
    <script>
        // DATOS DE PRODUCTOS
        const todosProductos = {productos_json};
        let productosFiltrados = [];
        let productosPorPagina = 24;
        let paginaActual = 1;
        let categoriaActual = 'motos';
        let productoActual = null;
        let metodoPagoSeleccionado = 'nequi';
        
        // INICIALIZACIÓN
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('Catálogo cargado con ' + todosProductos.length + ' productos');
            inicializarFiltros();
            mostrarProductos();
            inicializarAutocompletado();
            inicializarModal();
        }});
        
        function inicializarFiltros() {{
            // Inicializar filtro de marcas
            const marcasUnicas = [...new Set(todosProductos.map(p => p.marca))].sort();
            const marcaFilter = document.getElementById('marcaFilter');
            
            marcasUnicas.forEach(marca => {{
                const option = document.createElement('option');
                option.value = marca;
                option.textContent = marca;
                marcaFilter.appendChild(option);
            }});
            
            // Evento para búsqueda
            const searchInput = document.getElementById('searchInput');
            searchInput.addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    buscarProductos();
                }}
            }});
            
            // Filtrar por categoría inicial
            productosFiltrados = todosProductos.filter(p => p.categoria === categoriaActual);
            actualizarContador();
        }}
        
        function inicializarAutocompletado() {{
            const searchInput = document.getElementById('searchInput');
            const autocompleteList = document.getElementById('autocompleteList');
            
            searchInput.addEventListener('input', function() {{
                const termino = this.value.toLowerCase();
                
                if (termino.length < 2) {{
                    autocompleteList.style.display = 'none';
                    return;
                }}
                
                // Filtrar productos que coincidan
                const sugerencias = todosProductos.filter(producto => {{
                    return producto.nombre.toLowerCase().includes(termino) ||
                           producto.marca.toLowerCase().includes(termino) ||
                           producto.descripcion.toLowerCase().includes(termino);
                }}).slice(0, 10); // Limitar a 10 sugerencias
                
                if (sugerencias.length > 0) {{
                    let html = '';
                    sugerencias.forEach(producto => {{
                        html += `
                            <div class="autocomplete-item" onclick="seleccionarAutocompletado('${{producto.id}}')">
                                <i class="fas fa-search" style="color: var(--primary);"></i>
                                <div class="product-name">${{producto.nombre.substring(0, 40)}}${{producto.nombre.length > 40 ? '...' : ''}}</div>
                                <div class="product-brand">${{producto.marca}}</div>
                                <div class="product-price">${{producto.precio_str}}</div>
                            </div>
                        `;
                    }});
                    
                    autocompleteList.innerHTML = html;
                    autocompleteList.style.display = 'block';
                }} else {{
                    autocompleteList.style.display = 'none';
                }}
            }});
            
            // Cerrar autocompletado al hacer clic fuera
            document.addEventListener('click', function(e) {{
                if (!searchInput.contains(e.target) && !autocompleteList.contains(e.target)) {{
                    autocompleteList.style.display = 'none';
                }}
            }});
        }}
        
        function seleccionarAutocompletado(productoId) {{
            const producto = todosProductos.find(p => p.id == productoId);
            if (producto) {{
                document.getElementById('searchInput').value = producto.nombre;
                document.getElementById('autocompleteList').style.display = 'none';
                buscarProductos();
            }}
        }}
        
        function buscarProductos() {{
            const searchInput = document.getElementById('searchInput');
            const termino = searchInput.value.toLowerCase();
            
            if (!termino) {{
                productosFiltrados = todosProductos.filter(p => p.categoria === categoriaActual);
            }} else {{
                productosFiltrados = todosProductos.filter(producto => {{
                    if (producto.categoria !== categoriaActual) return false;
                    
                    return producto.nombre.toLowerCase().includes(termino) ||
                           producto.marca.toLowerCase().includes(termino) ||
                           producto.descripcion.toLowerCase().includes(termino);
                }});
            }}
            
            paginaActual = 1;
            mostrarProductos();
            
            // Actualizar sugerencias
            const suggestions = document.getElementById('searchSuggestions');
            if (productosFiltrados.length === 0 && termino) {{
                suggestions.innerHTML = '<i class="fas fa-exclamation-circle"></i> No se encontraron resultados. Intenta con otras palabras.';
                suggestions.style.color = '#ff9999';
            }} else if (termino) {{
                suggestions.innerHTML = '<i class="fas fa-check-circle"></i> ' + productosFiltrados.length + ' resultados encontrados';
                suggestions.style.color = '#25D366';
            }} else {{
                suggestions.innerHTML = '<i class="fas fa-lightbulb"></i> <strong>Búsqueda inteligente:</strong> Escribe para ver sugerencias automáticas.';
                suggestions.style.color = 'rgba(255,255,255,0.7)';
            }}
        }}
        
        function filtrarPorCategoria(categoria) {{
            // Cambiar botones activos
            document.querySelectorAll('.categoria-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
            
            categoriaActual = categoria;
            productosFiltrados = todosProductos.filter(p => p.categoria === categoriaActual);
            
            // Resetear búsqueda
            document.getElementById('searchInput').value = '';
            document.getElementById('marcaFilter').value = '';
            document.getElementById('autocompleteList').style.display = 'none';
            
            paginaActual = 1;
            mostrarProductos();
            
            // Actualizar título
            document.getElementById('resultadosTitle').textContent = 
                categoria === 'motos' ? 'REPUESTOS PARA MOTOS' : 'REPUESTOS PARA CARROS';
        }}
        
        function aplicarFiltros() {{
            const marcaSeleccionada = document.getElementById('marcaFilter').value;
            const ordenSeleccionado = document.getElementById('ordenFilter').value;
            
            let filtrados = todosProductos.filter(p => p.categoria === categoriaActual);
            
            if (marcaSeleccionada) {{
                filtrados = filtrados.filter(p => p.marca === marcaSeleccionada);
            }}
            
            // Ordenar
            filtrados.sort((a, b) => {{
                switch(ordenSeleccionado) {{
                    case 'nombre': return a.nombre.localeCompare(b.nombre);
                    case 'precio_asc': return a.precio - b.precio;
                    case 'precio_desc': return b.precio - a.precio;
                    case 'marca': return a.marca.localeCompare(b.marca);
                    default: return 0;
                }}
            }});
            
            productosFiltrados = filtrados;
            paginaActual = 1;
            mostrarProductos();
        }}
        
        function mostrarProductos() {{
            const productGrid = document.getElementById('productGrid');
            const totalPaginas = Math.ceil(productosFiltrados.length / productosPorPagina);
            
            const inicio = (paginaActual - 1) * productosPorPagina;
            const fin = inicio + productosPorPagina;
            const productosPagina = productosFiltrados.slice(inicio, fin);
            
            let html = '';
            
            productosPagina.forEach(producto => {{
                const estrellas = '★★★★★';
                const ratingHtml = `<div class="product-rating">${{estrellas}} <span style="font-size: 14px; color: #ccc; margin-left: 10px;">${{producto.comentarios}} comentarios</span></div>`;
                
                const onerrorScript = `this.onerror=null; this.src='https://via.placeholder.com/400x300/1a237e/FFFFFF?text=${{encodeURIComponent(producto.marca.substring(0,15))}}';`;
                
                html += `
                    <div class="product-card">
                        <img src="${{producto.imagen}}" 
                             alt="${{producto.nombre}}" 
                             class="product-image"
                             onerror="${{onerrorScript}}">
                        
                        <div class="product-info">
                            <div class="product-marca">${{producto.marca}}</div>
                            <h3 class="product-nombre">${{producto.nombre}}</h3>
                            <p style="color: rgba(255,255,255,0.7); font-size: 14px; margin: 10px 0; line-height: 1.5; min-height: 60px;">${{producto.descripcion}}</p>
                            
                            ${{ratingHtml}}
                            
                            <div style="background: rgba(37, 211, 102, 0.1); padding: 10px 15px; border-radius: 10px; margin: 15px 0; border: 1px solid rgba(37, 211, 102, 0.3);">
                                <i class="fas fa-shipping-fast" style="color: #25D366;"></i>
                                <span style="color: #ccc; font-size: 14px;">Envío según ubicación - Acordar en WhatsApp</span>
                            </div>
                            
                            <div class="product-precio">${{producto.precio_str}}</div>
                            
                            <button class="btn-pagar" onclick="abrirModalPago(${{producto.id}})">
                                <i class="fas fa-credit-card"></i> PAGA AHORA
                            </button>
                            
                            <button class="btn-whatsapp" onclick="consultarProductoWhatsApp(${{producto.id}})">
                                <i class="fab fa-whatsapp"></i> CONSULTAR
                            </button>
                        </div>
                    </div>
                `;
            }});
            
            if (productosPagina.length === 0) {{
                html = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 60px; background: rgba(26, 35, 126, 0.1); border-radius: 20px; border: 2px dashed rgba(255,255,255,0.2);">
                        <i class="fas fa-search fa-4x" style="margin-bottom: 20px; color: rgba(255,255,255,0.3);"></i>
                        <h3 style="color: white; margin-bottom: 15px;">No se encontraron productos</h3>
                        <p style="color: rgba(255,255,255,0.7); margin-bottom: 25px;">Intenta con otros términos de búsqueda o cambia los filtros</p>
                        <button onclick="resetFiltros()" style="margin-top: 15px; padding: 10px 20px; background: var(--primary); color: white; border: none; border-radius: 8px; cursor: pointer;">
                            Mostrar todos los productos
                        </button>
                    </div>
                `;
            }}
            
            productGrid.innerHTML = html;
            
            // Actualizar controles
            document.getElementById('currentPage').textContent = paginaActual;
            document.getElementById('totalPages').textContent = totalPaginas || 1;
            document.getElementById('prevPage').disabled = paginaActual <= 1;
            document.getElementById('nextPage').disabled = paginaActual >= totalPaginas;
            
            actualizarContador();
        }}
        
        function cambiarPagina(direccion) {{
            const nuevaPagina = paginaActual + direccion;
            const totalPaginas = Math.ceil(productosFiltrados.length / productosPorPagina);
            
            if (nuevaPagina >= 1 && nuevaPagina <= totalPaginas) {{
                paginaActual = nuevaPagina;
                mostrarProductos();
            }}
        }}
        
        function resetFiltros() {{
            document.getElementById('searchInput').value = '';
            document.getElementById('marcaFilter').value = '';
            document.getElementById('ordenFilter').value = 'nombre';
            document.getElementById('autocompleteList').style.display = 'none';
            
            productosFiltrados = todosProductos.filter(p => p.categoria === categoriaActual);
            paginaActual = 1;
            mostrarProductos();
            
            document.getElementById('searchSuggestions').innerHTML = '<i class="fas fa-lightbulb"></i> <strong>Búsqueda inteligente:</strong> Escribe para ver sugerencias automáticas.';
            document.getElementById('searchSuggestions').style.color = 'rgba(255,255,255,0.7)';
        }}
        
        function actualizarContador() {{
            const total = productosFiltrados.length;
            const inicio = (paginaActual - 1) * productosPorPagina + 1;
            const fin = Math.min(inicio + productosPorPagina - 1, total);
            
            let mensaje = `Mostrando ${{inicio}}-${{fin}} de ${{total}} productos`;
            
            if (productosFiltrados.length < todosProductos.length) {{
                mensaje += ` (filtrados de ${{todosProductos.length}} totales)`;
            }}
            
            document.getElementById('productosCount').textContent = mensaje;
        }}
        
        // MODAL DE PAGO - MEJORADO
        function inicializarModal() {{
            // Selección de método de pago
            document.querySelectorAll('.payment-method').forEach(method => {{
                method.addEventListener('click', function() {{
                    seleccionarMetodoPago(this.getAttribute('data-tipo'));
                }});
            }});
        }}
        
        function seleccionarMetodoPago(tipo) {{
            // Remover selección anterior
            document.querySelectorAll('.payment-method').forEach(method => {{
                method.classList.remove('selected');
            }});
            
            // Seleccionar nueva opción
            document.querySelector(`.payment-method[data-tipo="${{tipo}}"]`).classList.add('selected');
            metodoPagoSeleccionado = tipo;
            
            // Actualizar enlace de Wompi si hay un producto seleccionado
            if (productoActual) {{
                actualizarEnlaceWompi();
            }}
        }}
        
        function abrirModalPago(productoId) {{
            productoActual = todosProductos.find(p => p.id == productoId);
            
            if (!productoActual) return;
            
            // Actualizar información del producto en el modal
            document.getElementById('modalProductImage').src = productoActual.imagen;
            document.getElementById('modalProductImage').onerror = function() {{
                this.src = 'https://via.placeholder.com/400x300/1a237e/FFFFFF?text=' + encodeURIComponent(productoActual.marca.substring(0,15));
            }};
            
            document.getElementById('modalProductBrand').textContent = productoActual.marca;
            document.getElementById('modalProductName').textContent = productoActual.nombre;
            document.getElementById('modalProductPrice').textContent = productoActual.precio_str;
            
            // Actualizar cálculos de comisiones
            const comisiones = productoActual.comisiones;
            
            // Formatear valores monetarios
            function formatCurrency(value) {{
                return '$' + Math.round(value).toLocaleString('es-CO');
            }}
            
            // Nequi
            document.getElementById('nequiComision').textContent = formatCurrency(comisiones.nequi.comision);
            document.getElementById('nequiIva').textContent = formatCurrency(comisiones.nequi.iva);
            document.getElementById('nequiTotal').textContent = 'Total a pagar: ' + formatCurrency(comisiones.nequi.total);
            
            // Tarjeta
            document.getElementById('tarjetaComision').textContent = formatCurrency(comisiones.tarjeta.comision);
            document.getElementById('tarjetaIva').textContent = formatCurrency(comisiones.tarjeta.iva);
            document.getElementById('tarjetaTotal').textContent = 'Total a pagar: ' + formatCurrency(comisiones.tarjeta.total);
            
            // PSE
            document.getElementById('pseComision').textContent = formatCurrency(comisiones.pse.comision);
            document.getElementById('pseIva').textContent = formatCurrency(comisiones.pse.iva);
            document.getElementById('pseTotal').textContent = 'Total a pagar: ' + formatCurrency(comisiones.pse.total);
            
            // Seleccionar primera opción por defecto
            seleccionarMetodoPago('nequi');
            
            // Mostrar modal
            document.getElementById('pagoModal').style.display = 'block';
            document.body.style.overflow = 'hidden';
        }}
        
        function actualizarEnlaceWompi() {{
            if (!productoActual) return;
            
            let totalPagar = 0;
            let metodoNombre = '';
            
            if (metodoPagoSeleccionado === 'nequi') {{
                totalPagar = productoActual.comisiones.nequi.total;
                metodoNombre = 'Nequi/Bancolombia';
            }} else if (metodoPagoSeleccionado === 'tarjeta') {{
                totalPagar = productoActual.comisiones.tarjeta.total;
                metodoNombre = 'Tarjeta débito/crédito';
            }} else if (metodoPagoSeleccionado === 'pse') {{
                totalPagar = productoActual.comisiones.pse.total;
                metodoNombre = 'PSE';
            }}
            
            // Crear enlace Wompi (usando el link base)
            const wompiBtn = document.getElementById('modalBtnWompi');
            wompiBtn.href = "{link_pago_base}";
            
            // También preparamos un mensaje para WhatsApp en caso de que quieran enviar comprobante
            const mensajeWhatsApp = `Hola! Quiero comprar el siguiente producto:%0A%0A` +
                `*Producto:* ${{productoActual.nombre}}%0A` +
                `*Marca:* ${{productoActual.marca}}%0A` +
                `*Precio base:* ${{productoActual.precio_str}}%0A` +
                `*Método de pago:* ${{metodoNombre}}%0A` +
                `*Total a pagar:* ${{formatCurrency(totalPagar)}}%0A%0A` +
                `Ya realicé el pago en Wompi. ¿Cuál es el siguiente paso?`;
            
            // Guardar el mensaje en un atributo data para usarlo después
            wompiBtn.setAttribute('data-whatsapp-msg', mensajeWhatsApp);
        }}
        
        function consultarWhatsApp() {{
            if (!productoActual) return;
            
            let totalPagar = 0;
            let metodoNombre = '';
            
            if (metodoPagoSeleccionado === 'nequi') {{
                totalPagar = productoActual.comisiones.nequi.total;
                metodoNombre = 'Nequi/Bancolombia';
            }} else if (metodoPagoSeleccionado === 'tarjeta') {{
                totalPagar = productoActual.comisiones.tarjeta.total;
                metodoNombre = 'Tarjeta débito/crédito';
            }} else if (metodoPagoSeleccionado === 'pse') {{
                totalPagar = productoActual.comisiones.pse.total;
                metodoNombre = 'PSE';
            }}
            
            // Mensaje de WhatsApp mejorado y claro
            const mensajeWhatsApp = `Hola! Estoy interesado en comprar:%0A%0A` +
                `📦 *Producto:* ${{productoActual.nombre}}%0A` +
                `🏷️ *Marca:* ${{productoActual.marca}}%0A` +
                `💰 *Precio base:* ${{productoActual.precio_str}}%0A` +
                `💳 *Método seleccionado:* ${{metodoNombre}}%0A` +
                `✅ *Total a pagar:* ${{formatCurrency(totalPagar)}}%0A%0A` +
                `¿Podrías confirmarme disponibilidad y proceder con la compra?`;
            
            window.open(`https://wa.me/{whatsapp_numero}?text=${{encodeURIComponent(mensajeWhatsApp)}}`, '_blank');
        }}
        
        function consultarProductoWhatsApp(productoId) {{
            const producto = todosProductos.find(p => p.id == productoId);
            if (!producto) return;
            
            // Mensaje de WhatsApp mejorado y claro
            const mensajeWhatsApp = `Hola! Me interesa este producto:%0A%0A` +
                `📦 *Producto:* ${{producto.nombre}}%0A` +
                `🏷️ *Marca:* ${{producto.marca}}%0A` +
                `💰 *Precio:* ${{producto.precio_str}}%0A%0A` +
                `¿Podrías darme más información?`;
            
            window.open(`https://wa.me/{whatsapp_numero}?text=${{encodeURIComponent(mensajeWhatsApp)}}`, '_blank');
        }}
        
        function cerrarModal() {{
            document.getElementById('pagoModal').style.display = 'none';
            document.body.style.overflow = 'auto';
            productoActual = null;
        }}
        
        // Función auxiliar para formatear moneda
        function formatCurrency(value) {{
            return '$' + Math.round(value).toLocaleString('es-CO');
        }}
        
        // Cerrar modal al hacer clic fuera
        window.addEventListener('click', function(event) {{
            const modal = document.getElementById('pagoModal');
            if (event.target === modal) {{
                cerrarModal();
            }}
        }});
        
        // Cerrar modal con ESC
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                cerrarModal();
            }}
        }});
        
        // Exponer funciones al scope global
        window.filtrarPorCategoria = filtrarPorCategoria;
        window.buscarProductos = buscarProductos;
        window.aplicarFiltros = aplicarFiltros;
        window.resetFiltros = resetFiltros;
        window.cambiarPagina = cambiarPagina;
        window.abrirModalPago = abrirModalPago;
        window.cerrarModal = cerrarModal;
        window.consultarProductoWhatsApp = consultarProductoWhatsApp;
        window.consultarWhatsApp = consultarWhatsApp;
        window.seleccionarAutocompletado = seleccionarAutocompletado;
        window.seleccionarMetodoPago = seleccionarMetodoPago;
    </script>
</body>
</html>'''
        
        # 7. GUARDAR ARCHIVO
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ ¡Catálogo mejorado generado exitosamente!")
        print(f"📁 Archivo: {archivo_salida}")
        print(f"📊 Productos incluidos: {len(productos)}")
        print(f"🏷️  Marcas únicas: {len(marcas_unicas)}")
        print(f"⬆️  Botones de categoría subidos y mejor posicionados")
        print(f"💳 Modal de pago completamente reorganizado")
        print(f"🔗 Botón Wompi dirige directamente a Wompi")
        print(f"💬 Mensajes de WhatsApp claros y organizados")
        print(f"📱 Botones flotantes: WhatsApp y TikTok")
        print(f"📱✅ Responsive optimizado para: Computadores, Tablets y Celulares")
        
        # Estadísticas
        print("\n📈 ESTADÍSTICAS DETALLADAS:")
        productos_con_precio = [p for p in productos if p['precio'] > 0]
        if productos_con_precio:
            precio_promedio = sum(p['precio'] for p in productos_con_precio) / len(productos_con_precio)
            precio_max = max(p['precio'] for p in productos_con_precio)
            precio_min = min(p['precio'] for p in productos_con_precio)
            
            print(f"   • Productos con precio definido: {len(productos_con_precio)}")
            print(f"   • Precio promedio: ${precio_promedio:,.0f}".replace(',', '.'))
            print(f"   • Precio más alto: ${precio_max:,.0f}".replace(',', '.'))
            print(f"   • Precio más bajo: ${precio_min:,.0f}".replace(',', '.'))
        
        print(f"   • Tamaño del archivo HTML: {os.path.getsize(archivo_salida) / 1024 / 1024:.2f} MB")
        
        # Abrir automáticamente
        try:
            import webbrowser
            ruta_absoluta = os.path.abspath(archivo_salida)
            webbrowser.open(f'file:///{ruta_absoluta}')
            print(f"\n🌐 Abriendo catálogo en el navegador...")
        except:
            print(f"\n💡 Abre manualmente: {archivo_salida}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("="*80)
    print("🏍️  CATÁLOGO DIGITAL TIKTOK MOTOR PARTS & TEMPLO GARAGE STREET 🏍️")
    print("="*80)
    
    print("\nEste script generará un catálogo digital con:")
    print("  ✓ Portada con imagen de fondo y logos duales")
    print("  ✓ Texto llamativo: 'PROTEGEMOS TODAS TUS PARTES'")
    print("  ✓ Botones de categoría mejor posicionados")
    print("  ✓ Búsqueda con autocompletado")
    print("  ✓ Modal de pago completamente reorganizado")
    print("  ✓ Botón Wompi que dirige directamente a Wompi")
    print("  ✓ Mensajes de WhatsApp claros y organizados")
    print("  ✓ Botones flotantes: WhatsApp y TikTok")
    print("  ✓ Optimizado para: Computadores, Tablets y Celulares")
    print("  ✓ TikToks oficiales: @brujablanca51 y @naturista_venuz")
    print("="*80)
    
    # Verificar dependencias
    try:
        import pandas as pd
        print("✅ pandas instalado correctamente")
    except ImportError:
        print("❌ pandas no está instalado. Instálalo con:")
        print("   pip install pandas openpyxl")
        input("\nPresiona Enter para salir...")
        return
    
    # Ejecutar generación
    respuesta = input("\n¿Generar el catálogo ahora? (s/n): ").lower()
    
    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n" + "="*80)
        print("🚀 INICIANDO GENERACIÓN DEL CATÁLOGO MEJORADO...")
        print("="*80)
        
        if generar_catalogo_completo():
            print("\n" + "="*80)
            print("🎉 ¡CATÁLOGO LISTO CON TODAS LAS MEJORAS!")
            print("="*80)
            
            print("\n📋 MEJORAS IMPLEMENTADAS:")
            print("1. ✅ Botones de categoría SUBIDOS y mejor posicionados")
            print("2. ✅ Modal de pago completamente REORGANIZADO y mejor diseñado")
            print("3. ✅ Botón 'PAGAR CON WOMPI' dirige DIRECTAMENTE a Wompi")
            print("4. ✅ Mensajes de WhatsApp CLAROS y ORGANIZADOS (sin descripción larga)")
            print("5. ✅ Botón flotante de TikTok (@brujablanca51) agregado")
            print("6. ✅ Responsive OPTIMIZADO para: Computadores, Tablets y Celulares")
            print("7. ✅ Animaciones y diseño mejorados en todo el catálogo")
            
            print("\n📱 DISPOSITIVOS COMPATIBLES:")
            print("   • Computadores (1200px+) - Diseño completo")
            print("   • Tablets (768px-992px) - Adaptado perfectamente")
            print("   • Celulares (<768px) - Totalmente responsive")
            print("   • Tablets en vertical/horizontal - Ajustes específicos")
            
            print("\n🔗 PARA COMPARTIR:")
            print("   • Sube 'catalogo_completo_final.html' a GitHub")
            print("   • Activa GitHub Pages en Settings > Pages")
            print("   • Comparte la URL generada")
            print("="*80)
        else:
            print("\n❌ Hubo un error durante la generación.")
    else:
        print("\n💡 Para ejecutar más tarde:")
        print("   Guarda este archivo como 'catalogo_final.py' y ejecuta:")
        print("   python catalogo_final.py")

if __name__ == "__main__":
    main()