<br><div align="center">

# SF — Santa Fuerza
### Sistema de Gestión para Gimnasio · Aplicación de Escritorio Local

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite)
![pywebview](https://img.shields.io/badge/pywebview-Desktop-blueviolet?style=flat-square)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?style=flat-square)

</div>

---

## Descripción

**Santa Fuerza** es una aplicación de escritorio multiplataforma (macOS / Windows) para la gestión integral de un gimnasio. Funciona sin conexión a internet, almacena todos los datos localmente y se presenta como una ventana nativa mediante **pywebview**, que envuelve un servidor **Flask** embebido.

El sistema cubre el ciclo operativo completo: registro de clientes con membresías, punto de venta (POS), inventario de productos, gestión de empleados y reportes de ventas con filtros por empleado y rango de fechas.

---

## Stack Tecnológico

| Capa | Tecnología | Rol |
|---|---|---|
| **Backend** | Python 3.11 + Flask | API REST embebida, lógica de negocio |
| **Base de datos** | SQLite 3 + SQLAlchemy ORM | Persistencia local en `~/.santa_fuerza/` |
| **Frontend** | Vanilla JS (SPA) + HTML5 + CSS3 | Interfaz de usuario, carga dinámica de vistas |
| **Escritorio** | pywebview | Contenedor de ventana nativa (macOS & Windows) |
| **Tipografía** | Google Fonts (Outfit, Bebas Neue, Black Ops One) | Design system |
| **Iconos** | Font Awesome 6 | Iconografía de la interfaz |

---

## Arquitectura

```
palazuelos_mac_app/
├── app.py              # Servidor Flask: rutas, API REST, decoradores de auth
├── database.py         # Modelos SQLAlchemy (7 tablas)
├── requirements.txt    # Dependencias del proyecto
├── start_mac.command   # Script de arranque macOS
├── start_windows.bat   # Script de arranque Windows
├── static/
│   ├── css/style.css   # Design system completo (glassmorphism, dark mode)
│   └── js/main.js      # Orquestador SPA: navegación, modales, fetch API
└── templates/
    ├── base.html        # Shell SPA con sidebar RBAC-aware
    ├── login.html       # Pantalla de autenticación con canvas de partículas
    ├── setup.html       # Configuración inicial (primer arranque)
    ├── dashboard.html   # Panel de estadísticas en tiempo real
    ├── clients.html     # Gestión de clientes y membresías
    ├── pos.html         # Punto de Venta
    ├── inventory.html   # Catálogo de productos
    ├── plans.html       # Planes de membresía
    ├── employees.html   # Gestión de usuarios (solo admin)
    └── reports.html     # Reportes de ventas con paginación
```

### Modelo de Datos (7 tablas)

```
users ──────────────────────────────► sales ─────► sale_items
                                        ▲               │
clients ──► memberships ──► membership_plans     products ◄─┘
      └────────────────────────────────► sales
```

---

## Control de Acceso (RBAC)

El sistema implementa **Control de Acceso Basado en Roles** con dos niveles, aplicado mediante decoradores de Flask en el backend y renderizado condicional Jinja2 en el frontend:

| Rol | Módulos accesibles |
|---|---|
| `admin` | Dashboard · POS · Clientes · **Empleados · Planes · Inventario · Reportes** |
| `employee` | Dashboard · POS · Clientes |

**Implementación backend:**
```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            return jsonify({'success': False, 'message': 'Acceso restringido'}), 403
        return f(*args, **kwargs)
    return decorated_function
```

---

## Seguridad — Decisiones de Arquitectura

### Contraseñas en texto plano · Riesgo Aceptado y Documentado

> **Clasificación: Riesgo Aceptado / Decisión de Diseño Deliberada**

Las contraseñas de usuario se almacenan en texto plano en la base de datos SQLite. Esta es una **decisión arquitectónica consciente**, no un descuido, justificada por el modelo de amenaza específico de esta aplicación:

- La aplicación corre **exclusivamente de forma local** (pywebview + servidor Flask en `127.0.0.1`) y **no está expuesta a ninguna red**.
- La base de datos reside en `~/.santa_fuerza/`, con acceso físico restringido al sistema operativo del equipo.
- Comprometer las credenciales requeriría acceso previo al sistema operativo completo; en ese escenario, el hash de contraseñas no agrega protección material.
- El texto plano **facilita el soporte técnico in-situ** y la recuperación manual de cuentas por el administrador del sistema sin herramientas externas.

**Condición de revisión:** Esta decisión debe reevaluarse si el sistema expone algún endpoint a una red local (LAN) o pública, o si la base de datos se sincroniza con un servidor remoto.

### Secret Key

Gestionada vía variable de entorno con fallback para desarrollo:
```python
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_santa_fuerza_local')
```

---

## Instalación y Arranque

### Prerrequisitos
- Python 3.11+
- pip

### Instalación
```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/palazuelos_mac_app.git
cd palazuelos_mac_app

# 2. Crear entorno virtual
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Arranque

**macOS:**
```bash
bash start_mac.command
```

**Windows:**
```batch
start_windows.bat
```

**Desarrollo directo:**
```bash
python app.py
```

La base de datos se crea automáticamente en `~/.santa_fuerza/gym_database.sqlite` en el primer arranque. La aplicación redirige a la pantalla de configuración inicial para crear el usuario administrador.

---

## Módulos del Sistema

| Módulo | Endpoint API | Descripción |
|---|---|---|
| Dashboard | `GET /api/dashboard/stats` | Membresías activas, por vencer, vencidas e ingresos del día |
| Clientes | `GET/POST /api/clients` | Gestión con paginación, búsqueda y filtro por estado |
| Punto de Venta | `POST /api/sales` | Procesa ventas de productos y visitas; descuenta stock |
| Inventario | `GET/POST /api/products` | Catálogo de productos con control de stock |
| Planes | `GET/POST /api/plans` | Planes de membresía con duración en días y precio |
| Empleados | `GET/POST /api/employees` | Solo accesible con rol `admin` |
| Reportes | `GET /api/reports` | Ventas por empleado y rango de fechas con paginación |

---

## Licencia

Proyecto de uso interno. Todos los derechos reservados.
