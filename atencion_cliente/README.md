# NovaFibra Soporte 💬 — Atención al cliente automatizada con LLM

Chatbot de atención al cliente construido sobre la **API de OpenAI**. Atiende
consultas en lenguaje natural apoyándose en una base de conocimiento local,
simula consultas a sistemas internos y escala a un agente humano cuando el caso
lo requiere.

> **Proyecto académico.** NovaFibra es una empresa ficticia y todos los datos de
> `data/knowledge_base.json` están inventados.

---

## Objetivo

Demostrar el uso de un modelo de lenguaje como producto de cara al usuario
final: un asistente que resuelve consultas de soporte de primer nivel sin
intervención humana, sin inventar información y reconociendo sus propios
límites.

## Descripción

El asistente representa al equipo de soporte de **NovaFibra**, un proveedor de
internet de fibra óptica. Puede explicar planes y precios, resolver preguntas
frecuentes, orientar ante problemas técnicos comunes y recomendar el plan más
adecuado.

Lo que distingue al proyecto de un envoltorio simple sobre la API:

- **No improvisa.** El prompt de sistema restringe al modelo a la información
  de la base de conocimiento. Si le preguntan algo que no está ahí, lo admite y
  escala el caso en lugar de inventar una respuesta.
- **Escalamiento en dos capas.** Una capa determinista intercepta los casos que
  nunca deben quedar en manos del bot (asuntos legales, fraude, datos
  bancarios, petición explícita de una persona). La segunda deja que el propio
  modelo pida ayuda cuando no puede resolver.
- **Simulación de sistemas internos.** Ciertas consultas disparan acciones que
  en producción irían al CRM o a la plataforma de monitoreo. Sus resultados se
  inyectan en el contexto del modelo y se muestran en la interfaz.

## Funcionalidades

| Funcionalidad | Descripción |
|---|---|
| Chat en lenguaje natural | Interfaz de conversación sobre la API de OpenAI |
| Base de conocimiento | Servicios, precios, horarios, cargos, políticas y FAQ en JSON |
| Respuestas ancladas | El modelo solo puede usar la información suministrada |
| Historial de conversación | Las preguntas de seguimiento conservan el contexto |
| Acciones simuladas | Consulta de pedido, de cuenta y diagnóstico de línea |
| Escalamiento | Detección determinista + criterio del modelo |
| Tickets de soporte | Generación simulada con folio, prioridad y plazo |
| Nueva conversación | Reinicia historial y tickets de la sesión |
| Manejo de errores | Falta de clave, fallo de la API o base de conocimiento inválida |

## Arquitectura

```
Usuario
   │
   ▼
app.py  (Streamlit: chat, historial de sesión, tickets)
   │
   ▼
core/chatbot.py  ── AgenteSoporte.responder()
   │
   ├─ 1. core/escalamiento.py   reglas deterministas sobre el mensaje
   ├─ 2. core/acciones.py       consultas simuladas a sistemas internos
   ├─ 3. core/prompts.py        prompt de sistema + bloque DATOS CONSULTADOS
   │        └── core/knowledge_base.py   data/knowledge_base.json
   ├─ 4. API de OpenAI          client.responses.create(...)
   └─ 5. core/escalamiento.py   marcador [ESCALAR] → ticket simulado
```

Un turno de conversación recorre esas cinco etapas en orden. El cliente de
OpenAI se **inyecta** en `AgenteSoporte`, lo que permite ejercitar todo el flujo
en las pruebas con un cliente falso.

## Tecnologías utilizadas

| Componente | Uso |
|---|---|
| **Python 3.11** | Lenguaje base |
| **OpenAI Python SDK 3.3** | Cliente de la API, vía **Responses API** |
| **gpt-5.6-luna** | Modelo por defecto (configurable) |
| **Streamlit 1.62** | Interfaz web de chat |
| **python-dotenv** | Carga de la clave desde `.env` |
| **unittest** | Pruebas (biblioteca estándar, sin dependencias extra) |

### Sobre el modelo y la API

Se usa la **Responses API** (`client.responses.create`), la interfaz actual y
recomendada por OpenAI, en lugar de la antigua Chat Completions. El historial
se gestiona localmente y se envía como arreglo `input`, lo que mantiene el
control del contexto y del costo.

El modelo por defecto es **`gpt-5.6-luna`**: pertenece a la familia
GPT-5.6 y es la opción más económica de la generación actual, adecuada para un
asistente de soporte donde importan la latencia y el costo por conversación.
Se puede cambiar con la variable `OPENAI_MODEL`.

## Requisitos previos

- **Python 3.10 o superior** (verificado con 3.11.9).
- Una **clave de API de OpenAI** con crédito disponible
  (<https://platform.openai.com/api-keys>).
- Conexión a internet.

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/JackWayne98/llm.git
cd llm/atencion_cliente
```

### 2. Crear el entorno virtual

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar las dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar la clave de OpenAI

Copia la plantilla y edita el archivo resultante:

```bash
# Linux / macOS
cp .env.example .env
```

```powershell
# Windows
Copy-Item .env.example .env
```

Abre `.env` y sustituye el valor de ejemplo por tu clave real:

```
OPENAI_API_KEY=sk-...tu_clave...
```

Como alternativa puedes exportarla en la terminal sin crear el archivo:

```bash
export OPENAI_API_KEY="sk-...tu_clave..."     # Linux / macOS
$env:OPENAI_API_KEY = "sk-...tu_clave..."     # Windows PowerShell
```

> `.env` está en el `.gitignore` del repositorio: la clave nunca se versiona.

### 5. Ejecutar

```bash
streamlit run app.py
```

La aplicación abre en <http://localhost:8501>. Si Streamlit pide un correo al
arrancar, basta con pulsar Enter para omitirlo.

## Ejemplo de conversación

El siguiente intercambio ilustra el comportamiento previsto, incluida la
pregunta de seguimiento que depende del contexto anterior:

```
Tú:  ¿Cuánto cuesta el servicio premium?

Bot: El plan Fibra Premium cuesta 899 MXN al mes e incluye 1 Gbps simétrico.
     ¿Te comparto todo lo que trae incluido?

Tú:  ¿Y qué incluye?

Bot: Incluye router Wi-Fi 7 en comodato, instalación prioritaria en 24 horas,
     soporte prioritario 24/7, dos repetidores de malla, una IP fija y la
     suscripción a NovaTV sin costo adicional.
```

Consulta que dispara una acción simulada:

```
Tú:  Mi internet va muy lento desde ayer

     ⚙ Ejecutando diagnóstico remoto de la línea...
       Diagnóstico de línea: potencia óptica -19 dBm, latencia 12 ms,
       pérdida de paquetes 1 %. El enlace opera dentro de parámetros
       normales; la lentitud probablemente provenga de la red Wi-Fi interna.

Bot: Revisé tu línea y el enlace está en parámetros normales, así que la
     lentitud viene probablemente del Wi-Fi. Prueba reiniciando el router 30
     segundos y midiendo la velocidad por cable.
```

Consulta que se escala:

```
Tú:  Quiero hablar con un agente humano

Bot: Entiendo, te pongo en contacto con el equipo.

     ⚠ Caso escalado a un agente humano
     Ticket SOP-A31F0C · Prioridad Media
     Motivo: El cliente solicita hablar con una persona
     Respuesta estimada antes del 24/08/2026 a las 14:30
```

## Estructura del proyecto

```
atencion_cliente/
├── app.py                      # Interfaz Streamlit (punto de entrada)
├── core/
│   ├── __init__.py
│   ├── chatbot.py              # Orquestación y llamada a la API
│   ├── knowledge_base.py       # Carga y validación de la base de conocimiento
│   ├── prompts.py              # Prompt de sistema y formato de contexto
│   ├── acciones.py             # Simulación de sistemas internos
│   └── escalamiento.py         # Reglas de escalamiento y tickets
├── data/
│   └── knowledge_base.json     # Información ficticia de NovaFibra
├── tests/
│   ├── __init__.py
│   ├── test_agente.py          # Lógica del agente (cliente de OpenAI falso)
│   └── test_app.py             # Interfaz, con streamlit.testing
├── .env.example
├── requirements.txt
└── README.md
```

## Pruebas

```bash
python -m unittest discover -s tests -t . -v
```

Son **30 pruebas** que cubren la carga y validación de la base de conocimiento,
la construcción del prompt, la detección y el determinismo de las acciones
simuladas, las reglas de escalamiento, la generación de tickets, el recorte y
la propagación del historial, el manejo de errores de la API y el
comportamiento de la interfaz.

Todas usan un cliente de OpenAI falso, de modo que **se ejecutan sin clave y sin
consumir tokens**.

## Funcionalidades simuladas

Estas partes imitan sistemas que en producción serían externos. Devuelven datos
inventados de forma **determinista** —el mismo identificador produce siempre el
mismo resultado— para que la conversación se mantenga coherente entre turnos.

| Simulación | Disparador | Qué devuelve |
|---|---|---|
| Consulta de pedido | Folio (`NF-48120`) junto a palabras como *pedido* o *instalación* | Estado del pedido y fecha estimada |
| Consulta de cuenta | *saldo*, *recibo*, *factura*, *pago*, *adeudo* | Saldo, último pago y estado del servicio |
| Diagnóstico de línea | *lento*, *sin internet*, *no funciona*, *intermitente* | Potencia óptica, latencia, pérdida y veredicto |
| Ticket de soporte | Escalamiento por regla o por decisión del modelo | Folio, motivo, prioridad y plazo de respuesta |

No existe base de datos ni persistencia: todo vive en memoria durante la sesión.

## Limitaciones

- **Sin persistencia.** Historial y tickets se pierden al recargar la página o
  al pulsar «Nueva conversación». No hay base de datos.
- **Base de conocimiento estática.** Se carga al arrancar; modificarla requiere
  reiniciar la aplicación.
- **Sin autenticación.** No hay login ni identificación real del cliente; el
  identificador de sesión se genera al azar.
- **Recuperación de contexto elemental.** La base de conocimiento completa se
  envía en cada llamada. Es viable con este volumen, pero un catálogo grande
  exigiría búsqueda semántica (RAG) para no disparar el costo.
- **Sin function calling.** Las acciones se disparan por detección de palabras
  clave, no por decisión del modelo. Migrarlas a *tool calling* de OpenAI sería
  la evolución natural.
- **Historial acotado.** Se envían los últimos 12 turnos para contener el costo;
  las referencias muy anteriores pueden perderse.
- **El ejemplo de conversación es ilustrativo.** Refleja el flujo diseñado y las
  cifras reales de la base de conocimiento, pero la redacción exacta del modelo
  variará entre ejecuciones.
- **Un solo idioma.** Prompt, base de conocimiento e interfaz están en español.

## Seguridad

- La clave de API se lee de `OPENAI_API_KEY`; no aparece en ningún archivo.
- `.env` está en `.gitignore`; `.env.example` contiene solo un marcador.
- La clave no se registra en logs ni se muestra en la interfaz.
- El prompt instruye al asistente a no solicitar contraseñas ni datos completos
  de tarjetas, en línea con la política de privacidad de la base de
  conocimiento.
