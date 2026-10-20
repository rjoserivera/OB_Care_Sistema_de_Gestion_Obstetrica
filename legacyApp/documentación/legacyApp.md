# 📁 legacyApp - Integración con Sistema Heredado

## Descripción

`legacyApp` expone, en **solo lectura**, los controles prenatales registrados en el sistema anterior del hospital (base `legacy_obstetric`). Su único uso actual es mostrar el historial de controles previos de una paciente en las pantallas de ficha obstétrica de `matronaApp`.

La app no tiene vistas, URLs, templates ni admin propios: entrega un modelo y una función de servicio que otras apps consumen.

```
legacyApp/
├── models.py      # ControlesPrevios (managed = False)
├── services.py    # obtener_controles_previos(rut, limite=20)
├── tests.py       # Tests del servicio y del router (sin BD)
└── documentación/legacyApp.md
```

---

## 📊 Modelo: ControlesPrevios

Mapea la tabla `controles_previos` de la BD legacy. Django **no** crea ni migra esta tabla (`managed = False`).

```python
class Meta:
    managed = False
    db_table = 'controles_previos'
    ordering = ['-fecha_control']
```

| Grupo | Campos principales |
|-------|--------------------|
| Identificación del control | `paciente_rut` (formato `12345678-9`), `fecha_control`, `numero_control`, `tipo_control`, `consultorio_origen`, `profesional_nombre`, `profesional_tipo` |
| Edad gestacional | `semanas_gestacion`, `dias_gestacion`, `fur`, `fpp` |
| Antropometría | `peso_kg`, `talla_cm`, `imc`, `altura_uterina_cm`, `ganancia_peso_total_kg` |
| Signos vitales | `presion_sistolica`, `presion_diastolica`, `frecuencia_cardiaca_materna`, `temperatura_c`, `saturacion_o2` |
| Evaluación fetal | `fcf_lpm`, `movimientos_fetales`, `presentacion_fetal`, `situacion_fetal` |
| Laboratorio | `glucosa_mg_dl`, `hemoglobina_g_dl`, `hematocrito_pct`, `grupo_sanguineo`, `factor_rh`, `proteinuria`, `leucocitos_orina` |
| Infecciosos | `vih_resultado`/`vih_fecha_toma`/`vih_orden`, `vdrl_*`, `sgb_*` (incl. `sgb_profilaxis`), `toxoplasma_*`, `hepatitis_b_*` |
| Patologías (booleanos) | `diabetes_gestacional`, `hipertension_arterial`, `preeclampsia_leve`, `preeclampsia_severa`, `eclampsia`, `anemia`, `infeccion_urinaria`, `corioamnionitis`, `amenaza_parto_prematuro`, `rotura_prematura_membranas`, `otras_patologias` |
| Tratamiento | `medicamentos_activos`, `acido_folico`, `sulfato_ferroso`, `aspirina_profilactica`, `otros_tratamientos` |
| Historia obstétrica | `numero_gestas`, `numero_partos`, `partos_vaginales_previos`, `cesareas_previas`, `numero_abortos`, `hijos_vivos`, `paridad_formato` |
| Examen físico | `edema_grado`, `edema_localizacion`, `varices`, `reflejos_osteotendinosos` |
| Plan de parto / riesgo | `numero_aro`, `nivel_riesgo` (`ALTO`/`MEDIO`/`BAJO`), `tiene_plan_parto`, `realizo_visita_guiada` |
| Notas | `fecha_proximo_control`, `observaciones`, `indicaciones_medicas`, `motivo_consulta`, `turno`, `fecha_hora_registro`, `sistema_origen` |

La PK es el `id bigint AUTO_INCREMENT` de la tabla (implícito en Django). `paciente_rut` y `fecha_control` tienen índice.

El esquema de referencia y datos de ejemplo (5 controles del RUT `16293109-1`) están en `utilidad/legacy_obstetric (1).sql`.

---

## 🔧 Servicio: obtener_controles_previos

```python
from legacyApp.services import obtener_controles_previos

controles, legacy_disponible = obtener_controles_previos(persona.Rut)
```

- Retorna una **lista ya evaluada** con los últimos `limite` (por defecto 20) controles, ordenados por `fecha_control` descendente.
- Si la BD legacy no responde (`DatabaseError`), registra el error en el logger `legacyApp.services` y retorna `([], False)`. **La vista que lo llama no falla.**
- Si el RUT viene vacío, retorna `([], True)` sin consultar.

Se recomienda usar este servicio en lugar de consultar `ControlesPrevios` directamente: la BD legacy no debería poder tumbar pantallas clínicas.

### Uso actual (matronaApp)

Hoy `matronaApp/views.py` **no** usa el servicio: consulta `ControlesPrevios` directamente (`.filter(paciente_rut=persona.Rut).order_by('-fecha_control')[:20]`) en estas vistas:

| Vista | Template |
|-------|----------|
| `crear_ficha_obstetrica_persona` | `Matrona/crear_ficha_obstetrica.html` (tab "Historial de Controles Prenatales") |
| `editar_ficha_obstetrica` | `Matrona/crear_ficha_obstetrica.html` |
| `detalle_ficha_obstetrica` | `Matrona/detalle_ficha_obstetrica.html` (tab "Controles Previos (Historial Legacy)") |

Mientras no se migre al servicio, una caída de la BD legacy produce un error 500 en esas pantallas.

Migración sugerida en cada vista:

```python
controles_previos, legacy_disponible = obtener_controles_previos(persona.Rut)
context['legacy_disponible'] = legacy_disponible
```

En los templates, mostrar un aviso con `{% if legacy_disponible is False %}`. En el detalle, reemplazar `{{ controles_previos.count }}` por `{{ controles_previos|length }}`, porque el servicio devuelve una lista.

---

## ⚙️ Configuración de base de datos

En `obstetric_care/settings.py`:

```python
DATABASES = {
    'default': { ... 'NAME': 'obstetric_carebdd' ... },
    'legacy': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'legacy_obstetric',
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    },
}

DATABASE_ROUTERS = ['obstetric_care.dbrouters.LegacyRouter']
```

Ambas conexiones usan hoy las mismas variables `DB_*`.

### Router (`obstetric_care/dbrouters.py`)

| Método | Comportamiento para `legacyApp` |
|--------|---------------------------------|
| `db_for_read` | `'legacy'` |
| `db_for_write` | `None` (no asigna BD) |
| `allow_relation` | `True` |
| `allow_migrate` | `False` en cualquier BD |

### Montar la BD legacy en local

```bash
mysql -u root -p -e "CREATE DATABASE legacy_obstetric CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
mysql -u root -p legacy_obstetric < "utilidad/legacy_obstetric (1).sql"
python manage.py cargar_paciente_legacy
```

`cargar_paciente_legacy` crea en la BD principal la `Persona`/`Paciente` del RUT `16293109-1`, que tiene 5 controles en el dump legacy.

> El archivo está hoy en `medicoApp/management/cargar_paciente_legacy.py`, fuera de `commands/`, por lo que Django no lo registra. Para que el comando funcione debe moverse a `medicoApp/management/commands/`.

---

## 🧪 Tests

```bash
python -m pytest legacyApp/tests.py
```

No requieren MySQL: simulan el queryset y cubren el caso normal, la caída de la BD legacy, el RUT vacío y el router.

---

## ⚠️ Limitaciones conocidas

1. **La escritura no está bloqueada de forma estricta.** `db_for_write` devuelve `None`, lo que en Django significa "sin opinión": un `save()` sobre `ControlesPrevios` iría a `default` (y fallaría porque la tabla no existe ahí). La garantía de solo lectura hoy es por convención.
2. **Mismas credenciales que la BD principal.** Lo recomendable es un usuario MySQL con permiso solo `SELECT` sobre `legacy_obstetric`.
3. **matronaApp aún no usa `obtener_controles_previos`** (ver "Uso actual"), así que una caída de legacy sigue afectando las fichas obstétricas.
4. **El comando `cargar_paciente_legacy` no está registrado** (ver "Montar la BD legacy en local").
5. Los campos de resultado (`vih_resultado`, `vdrl_resultado`, `nivel_riesgo`, etc.) son texto libre; los templates comparan contra valores exactos (`POSITIVO`, `REACTIVO`, `ALTO`).

---

*Documentación de legacyApp - OB_CARE*
