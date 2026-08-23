# Actividad 7 — Proyectos con modelos de lenguaje

Este repositorio reúne los proyectos de la actividad de LLM. Cada uno vive en su
propia carpeta y es independiente del otro.

| Proyecto | Carpeta | Modelo | Qué hace |
|---|---|---|---|
| Asistente de escritura | [`asistente_escritura/`](./asistente_escritura) | Google Gemini | Corrige la redacción, sugiere continuaciones y redacta textos desde cero |
| **Atención al cliente** | [**`atencion_cliente/`**](./atencion_cliente) | OpenAI `gpt-5.6-luna` | Chatbot de soporte con base de conocimiento, acciones simuladas y escalamiento a un agente humano |

Las instrucciones completas de instalación y ejecución de cada proyecto están en
su propio README:

- [`atencion_cliente/README.md`](./atencion_cliente/README.md)
- La documentación del asistente de escritura es la que continúa más abajo.

---

# Asistente de Escritura Automática ✍️

Este es un proyecto sencillo de un Asistente de Escritura impulsado por Inteligencia Artificial utilizando **Streamlit** para la interfaz gráfica y **Google Gemini API** como modelo de lenguaje subyacente.

## 🚀 Funcionalidades

El asistente cuenta con tres funciones principales diseñadas para facilitar el proceso de escritura:

1. **Mejorar redacción y ortografía**: Permite pegar un texto existente para que la IA corrija errores gramaticales y mejore el estilo y fluidez del mismo.
2. **Sugerir continuación**: Si te quedas sin ideas, puedes escribir el inicio de un texto y el asistente redactará el siguiente párrafo de forma coherente.
3. **Escribir un texto desde cero**: Solo necesitas ingresar un tema (ej. "Un correo solicitando vacaciones") y seleccionar el tono deseado (Profesional, Casual, Creativo, Persuasivo, etc). El modelo generará el texto completo por ti.

## 🛠 Requisitos Previos

Para utilizar esta aplicación necesitas:

- Python 3.8 o superior instalado en tu sistema.
- Una **API Key de Google Gemini** (Puedes obtenerla gratuitamente en [Google AI Studio](https://aistudio.google.com/)).

## 📦 Instalación

1. Clona el repositorio o navega hasta la carpeta del proyecto en tu terminal:
   ```bash
   cd /Users/leonelmendiola/llm/asistente_escritura
   ```

2. (Recomendado) Crea un entorno virtual para instalar las dependencias sin afectar tu sistema:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Mac/Linux
   # venv\Scripts\activate   # En Windows
   ```

3. Instala las dependencias requeridas usando el archivo `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

## ▶️ Uso

Para iniciar la aplicación, asegúrate de tener tu entorno virtual activado y ejecuta el siguiente comando:

```bash
streamlit run app.py
```

- Al ejecutarlo por primera vez, Streamlit podría preguntarte tu correo electrónico. Puedes simplemente presionar **Enter** para omitir ese paso.
- La aplicación se abrirá automáticamente en tu navegador web predeterminado (usualmente en `http://localhost:8501`).
- En la interfaz, **ingresa tu API Key de Gemini** en el campo correspondiente para comenzar a usar todas las funcionalidades.

## 📚 Tecnologías Utilizadas

- [Python](https://www.python.org/)
- [Streamlit](https://streamlit.io/) (Interfaz de usuario web)
- [Google Generative AI](https://ai.google.dev/) (Modelo de IA)
