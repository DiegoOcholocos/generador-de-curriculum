# CVDiego8 Pro — Generador de Currículums Local / Local CV Generator

---

## 🇪🇸 Versión en Español

Este es un potente generador de CVs profesional diseñado para ejecutarse localmente. Permite crear, editar e importar datos de currículums con una vista previa en tiempo real y exportación a PDF de alta calidad.

### ✨ Características

- **Vista Previa en Tiempo Real**: Visualiza los cambios instantáneamente mientras escribes.
- **Multilingüe**: Soporte completo para generar CVs e interfaz en **Español** e **Inglés**.
- **Gestión de Perfiles**: Guarda múltiples versiones de tu currículum y cárgalas cuando las necesites.
- **Importación de CSV**: Carga datos masivamente desde archivos CSV siguiendo un formato sencillo.
- **Diferentes Estilos**: 10 temas de color y layouts profesionales (Clásica, Moderna, Elegante, etc.).
- **Privacidad Total**: Tus datos nunca salen de tu máquina; todo se genera localmente.

### 🚀 Requisitos e Instalación

1. Asegúrate de tener **Python 3.x** instalado.
2. Instala las dependencias necesarias:
   ```bash
   pip install flask reportlab
   ```
3. Ejecuta la aplicación:
   ```bash
   python app.py
   ```
4. Abre tu navegador en: `http://127.0.0.1:5050`

---

## 🇺🇸 English Version

This is a powerful, professional CV generator designed to run locally. It allows you to create, edit, and import resume data with real-time preview and high-quality PDF export.

### ✨ Features

- **Real-Time Preview**: Visualize changes instantly as you type.
- **Multi-language**: Full support for generating CVs and interface in **Spanish** and **English**.
- **Profile Management**: Save multiple versions of your resume and load them whenever needed.
- **CSV Import**: Bulk load data from CSV files following a simple format.
- **Professional Styles**: 10 color themes and professional layouts (Classic, Modern, Elegant, etc.).
- **Total Privacy**: Your data never leaves your machine; everything is generated locally.

### 🚀 Requirements and Installation

1. Ensure you have **Python 3.x** installed.
2. Install necessary dependencies:
   ```bash
   pip install flask reportlab
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Open your browser at: `http://127.0.0.1:5050`

---

## 📁 Estructura del Proyecto / Project Structure

- `app.py`: Servidor Flask / Flask Server.
- `pdf_generator.py`: Generador de PDF (ReportLab) / PDF Generator.
- `templates/index.html`: Interfaz de usuario (UI) / User Interface.
- `profiles/`: Datos guardados (JSON) / Saved profiles data.
