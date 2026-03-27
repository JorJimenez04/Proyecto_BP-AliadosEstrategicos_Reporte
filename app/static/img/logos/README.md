# Logos — AdamoServices Partner Manager

Coloca aquí los archivos de logo de la compañía.

## Nomenclatura recomendada

| Archivo | Uso |
|---|---|
| `logo_adamo_color.png` | Logo principal (fondo claro) |
| `logo_adamo_blanco.png` | Logo en blanco (fondo oscuro / sidebar) |
| `logo_adamo_isotipo.png` | Ícono / isotipo solo (sin texto) |
| `favicon.png` | Favicon del navegador (32×32 px) |

## Formatos aceptados por Streamlit

- **PNG** (recomendado — soporta transparencia)
- **SVG** (vectorial, ideal para logos)
- **JPG** / **JPEG**
- **WebP**

## Cómo usar los logos en la app

```python
from pathlib import Path

# Leer como archivo binario (para st.image o st.logo)
LOGO_DIR = Path(__file__).parent.parent / "static" / "img" / "logos"

# En el sidebar (Streamlit ≥ 1.26)
st.logo(str(LOGO_DIR / "logo_adamo_color.png"))

# Como imagen dentro de un componente
st.image(str(LOGO_DIR / "logo_adamo_blanco.png"), width=180)
```

## Tamaños recomendados

| Uso | Ancho | Alto |
|---|---|---|
| Sidebar (`st.logo`) | 240 px | auto |
| Cabecera | 200–300 px | auto |
| Favicon | 32 px | 32 px |
| Isotipo / ícono | 64–128 px | 64–128 px |

> Los archivos de imagen **no se versionan** si superan 1 MB.  
> Agrega `*.png` o `*.jpg` a `.gitignore` si los logos son confidenciales.
