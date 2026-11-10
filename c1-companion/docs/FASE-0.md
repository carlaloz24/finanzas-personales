# Fase 0 — Revisión técnica y decisiones

Fecha: 10 de noviembre de 2026

## Estado

| Bloque | Estado |
| --- | --- |
| Revisión de Astryx | Hecha |
| Arquitectura y carpetas | Hecha |
| Modelo de datos y persistencia (Dexie) | Implementado y con tests |
| Reglas nuevas: phrasal verbs y términos duplicados | Implementadas y con tests |
| Diseño visual / prototipo | **Detenido**: falta la skill `anti-ai-design` |

### Por qué está detenido el diseño

La especificación (apartado 10) exige leer la skill `anti-ai-design` antes de
diseñar la interfaz y, si no está disponible, parar y avisar. He buscado en las
skills del entorno de Claude Code (skills del sistema, `~/.claude/skills`,
skills sincronizadas de la cuenta y el repositorio) y no existe. No la he
sustituido por otra.

Para continuar, añade la skill por una de estas vías:

- Súbela a tus skills de claude.ai (Ajustes → Capacidades → Skills); se sincroniza en las sesiones nuevas.
- O confírmala en el repositorio en `.claude/skills/anti-ai-design/SKILL.md`.
  Ojo: el `.gitignore` de la raíz ignora `.claude/`, así que habría que añadir
  una excepción (`!.claude/skills/`).

## 1. Astryx

- Repositorio: `github.com/meta/astryx`. Licencia **MIT** (Meta Platforms, 2026). Uso personal sin problemas.
- Estado: **beta**. Paquete `@astryxdesign/core` 0.7.12 en npm, con publicaciones frecuentes.
- Requisitos: `react` y `react-dom` **≥ 19**, `@stylexjs/stylex` ^0.19 como peer.
- Vite: compatible sin plugins. Astryx se distribuye precompilado; basta con importar su CSS y el proveedor de tema.
- Temas oficiales: neutral, stone, matcha, butter, chocolate, gothic, y2k. Un tema es un conjunto de variables CSS, así que se puede ajustar sin hacer fork.
- La documentación de componentes se consulta con `npx @astryxdesign/cli component <Nombre>`. Usaré eso en lugar de inventar props.

**Decisión:** usar Astryx. Cumple licencia, stack y estilo minimalista. Riesgos:
al ser beta puede haber cambios entre versiones, así que fijaré la versión
exacta en `package.json`. No lo he instalado todavía porque los componentes se
eligen en la fase de diseño.

## 2. Persistencia: Dexie 4 sobre IndexedDB

Es la forma más sencilla de trabajar con IndexedDB: índices, transacciones y
soporte nativo de `Blob`. Base de datos `c1-companion`, versión 1:

| Tabla | Índices |
| --- | --- |
| `entries` | `id`, **`&[termKey+type]` (único)**, `termKey`, `type`, `*topicIds`, `*personalCategoryIds`, `learningStatus`, `createdAt` |
| `topics` | `id`, `name` |
| `categories` | `id`, `name` |
| `exams` | `id`, `date` |
| `attempts` | `id`, `examId`, `[examId+part]`, `date` |
| `mistakes` | `id`, `attemptId`, `type` |
| `attachments` | `id`, `attemptId` |

Los temas Cambridge (12) y las categorías personales (15) se crean la primera
vez que se abre la base de datos. Los cambios de esquema futuros se harán con
`version(n).upgrade()`, sin tocar versiones publicadas, para que **una
actualización nunca borre datos**.

Cambios respecto al modelo orientativo:

- `grammarDetails: Record<string,string>` se sustituye por bloques tipados por tipo (`noun`, `verb`, `connector`, `grammar`). Solo se guarda el bloque del tipo elegido; al cambiar el tipo se descartan los campos del anterior.
- Errores y adjuntos van en tablas propias, enlazadas por `attemptId`. Así se pueden listar todos los errores sin recorrer cada intento y los blobs no se cargan al abrir un intento.
- Cada adjunto indica su bloque (`original` o `correction`).

## 3. Reglas añadidas en esta iteración

**Phrasal verbs.** Van dentro del tipo `Verb`. El formulario de verbo tendrá una
casilla opcional «Phrasal verb»; si no se marca, el verbo es estándar
(`verb.isPhrasalVerb = false` por defecto). Los errores ya tenían un tipo «Phrasal verb».

**Sin duplicados.** No se puede introducir el mismo término dos veces con el mismo tipo. Con tipos distintos sí.

- La comparación ignora mayúsculas, espacios sobrantes y el tipo de apóstrofo: `Give up`, ` give   UP ` y `give up` cuentan como uno.
- Se comprueba al crear una entrada y al cambiar su término o su tipo. Hay dos capas: una comprobación previa con un mensaje claro («ya está en tu vocabulario», con acceso a la ficha existente) y el índice único de IndexedDB como red de seguridad.
- `record` (noun) y `record` (verb) son dos fichas distintas. Al enlazar el sinónimo «record» se elige cuál.
- Los términos son distintos aunque compartan raíz: `give` y `give up` son entradas diferentes.

## 4. Adjuntos

Se guardan como `Blob` en IndexedDB (tabla `attachments`), sin conversión a
base64. Al iniciar se pedirá `navigator.storage.persist()` para que el navegador
no libere el espacio cuando vaya justo de almacenamiento. Las fotos del móvil se
guardan tal cual; si el tamaño resulta un problema, se puede añadir más
adelante una compresión opcional en el navegador.

## 5. Exportación (Fase 5)

`fflate`: pequeño, sin dependencias y rápido con binarios. El ZIP seguirá la
estructura de la especificación. `data.json` contendrá todos los IDs y
relaciones, y los adjuntos tendrán como ruta `attachments/<examen>/<parte>/<intento>-<bloque>-<n>.<ext>`.
La misma ZIP sirve de copia de seguridad. Al importar se valida el `data.json`
(versión de formato y referencias) y se pide confirmación antes de sustituir
los datos.

## 6. PWA

Se deja para después. `npm run dev` / `npm run preview` ya funcionan sin
conexión una vez instalada la app en local. Más adelante se puede añadir
`vite-plugin-pwa` si quieres instalarla en el móvil.

## 7. Estructura

```
c1-companion/
├── docs/            especificación y decisiones
├── src/
│   ├── domain/      tipos, normalización, datos iniciales
│   ├── db/          esquema Dexie
│   ├── services/    lógica (vocabulario; después repaso, exámenes, exportación)
│   └── main.tsx     punto de entrada (interfaz pendiente)
└── index.html
```

## 8. Riesgos

- Astryx en beta: fijar la versión y actualizar a propósito.
- Los datos dependen del navegador y su perfil: borrar los datos del sitio elimina todo. Por eso la exportación es la copia de seguridad.
- Ubicación: la app está en una subcarpeta del repositorio `finanzas-personales`. Funciona igual, pero conviene moverla a su propio repositorio.

## Siguiente paso

Cuando esté disponible la skill `anti-ai-design`: prototipo navegable de Inicio,
Vocabulario (lista, alta rápida y ficha), Repasar y Exámenes para validarlo
antes de seguir con las fases 2 a 6.
