# C1 Advanced Companion — Especificación funcional y técnica

- **Proyecto:** aplicación personal local para preparar Cambridge C1 Advanced
- **Fecha:** 10 de noviembre de 2026
- **Estado:** definición inicial. Las decisiones marcadas como abiertas quedan a criterio de Claude, siempre que respete los principios del proyecto.

> **Cambios del 10/11/2026**
> 1. Los phrasal verbs se incluyen dentro del tipo **Verb**. Al añadir un verbo habrá una casilla opcional **Phrasal verb**. Si no se marca, se considera un verbo estándar (apartado 5.1).
> 2. **No se puede introducir un término dos veces** (apartado 5.1.1).

---

## 1. Visión del producto

### 1.1. Nombre, alcance y evolución

Nombre de trabajo: C1 Advanced Companion. Puede revisarse más adelante. No debe presentarse solo como una aplicación de vocabulario, porque reúne toda la preparación personal del examen.

**V1:** herramienta de uso exclusivamente personal, ejecutada en local, para preparar el Cambridge C1 Advanced. No es un producto comercial y no se dedica esfuerzo a funciones necesarias solo para publicar o escalar.

**Posible V2:** versión publicable en marketplaces (cuentas, sincronización, nube, onboarding, privacidad, seguridad, accesibilidad ampliada, distribución, soporte). Nada de eso entra en la V1 salvo que sea imprescindible para el uso personal. La arquitectura debe ser ordenada y ampliable, sin construir ahora la complejidad de la V2.

Objetivo: una aplicación web personal, rápida e intuitiva para registrar, organizar, consultar y estudiar vocabulario y estructuras de inglés. También debe registrar ejercicios y simulacros, conservar fotos del trabajo manuscrito y sus correcciones, guardar versiones mejoradas y documentar errores. Toda la información debe poder exportarse en formato estructurado para que Claude genere un documento de estudio personalizado.

### Principios no negociables

1. **Sencillez:** añadir, consultar y estudiar requiere pocos pasos.
2. **Uso personal y local:** sin cuentas, usuarios, backend ni nube.
3. **Coste cero:** sin servicios ni APIs de IA de pago ni infraestructura alojada.
4. **Privacidad:** los datos se quedan en el dispositivo salvo exportación manual.
5. **Persistencia:** cerrar la aplicación no borra los datos.
6. **Exportación completa** para trabajar en Claude.
7. **Diseño coherente** con Astryx, si compatibilidad y licencia lo permiten.
8. **No sobreconstruir.**

## 2. Alcance

**Incluido en la V1:** biblioteca de vocabulario; alta y edición rápida; temas Cambridge y categorías personales; sinónimos enlazados; búsqueda y filtros; flashcards; exámenes, partes e intentos; fotos y documentos adjuntos; correcciones, versiones mejoradas y errores; exportación para Claude; importación de copia de seguridad.

**Fuera del alcance:** cuentas, backend, base de datos remota, sincronización, APIs de IA, traducción o diccionario externo, OCR obligatorio, corrección automática, estadísticas avanzadas, gamificación, repetición espaciada compleja, compartir entre dispositivos.

Debe funcionar sin conexión. El uso de ChatGPT o Claude para corregir es externo a la aplicación.

## 3. Usuaria y contexto

Una única usuaria que prepara el C1 y quiere guardar vocabulario rápido, clasificarlo por temas y grupos propios, relacionar sinónimos, repasar, conservar un histórico de prácticas, aprender de sus errores y convertirlo todo en material de estudio final. No es un LMS ni una plataforma educativa comercial.

## 4. Navegación

Cuatro apartados: **Inicio**, **Vocabulario**, **Repasar**, **Exámenes**. La acción de añadir vocabulario siempre accesible con un botón claro, sin ser una sección propia.

Inicio: accesos rápidos y una visión general pequeña (número de entradas, último vocabulario añadido, continuar un examen). Sin dashboards con gráficas.

## 5. Vocabulario

### Captura rápida y entradas incompletas

- Guardar con solo **término y tipo**. El resto se completa después desde la ficha.
- Las entradas incompletas aparecen en búsquedas y se pueden editar.
- Sin sistema de tareas pendientes; como mucho, una indicación discreta de que faltan datos opcionales.

### 5.1. Alta de una entrada

| Campo | Requisito | Detalle |
| --- | --- | --- |
| Término | Obligatorio | Palabra, expresión o estructura. **Único** (5.1.1) |
| Tipo | Obligatorio | Una de las opciones de abajo |
| Significado | Opcional | Traducción o explicación en español |
| Sinónimos | Opcional | Lista de sinónimos |
| Antónimos | Opcional | Lista de antónimos |
| Ejemplo | Opcional | Frase en inglés |
| Traducción del ejemplo | Opcional | En español |
| Tema Cambridge | Opcional | Uno o varios |
| Categoría personal | Opcional | Una o varias |
| Notas | Opcional | Contexto, matices, recordatorios |
| Fecha | Automática | Creación y actualización |

**Tipos:** Noun · Verb · Adjective · Adverb · Expression · Connector · Grammar structure.

Idiom, Collocation y Expression se agrupan bajo **Expression**. No se crean tipos independientes para Idiom ni Collocation.

**Los phrasal verbs se incluyen dentro de Verb.** No se crea un tipo independiente.

#### Campos específicos (solo cuando corresponda)

**Noun:** Countable · Uncountable · Both.

**Verb:**
- **Phrasal verb:** casilla opcional. Si no se marca, el verbo se considera **estándar** por defecto.
- Past simple.
- Past participle.
- Preposición o patrón habitual, si resulta útil.

**Connector:**
- Función comunicativa: Addition, Contrast, Cause, Consequence, Example, Conclusion, Emphasis, Condition o Time.
- Categoría gramatical opcional: Adverb, Conjunction, Prepositional phrase o Connective expression. No se asume que todos los conectores sean adverbios.

**Grammar structure:** nombre de la estructura, fórmula o patrón, ejemplo en inglés, explicación o traducción, uso o contexto.
Ejemplos: Inversion (*Rarely have I seen…*), Conditional (*Had I known…, I would have…*), Cleft sentence (*What I find interesting is…*), Participle clause (*Having finished the task,…*), Concession (*Much as I agree with you,…*), Hedging (*It would appear that…*).

Los campos específicos no aparecen en el formulario si no corresponden al tipo elegido.

#### 5.1.1. Términos únicos

- **No se puede introducir un término dos veces.**
- La comparación ignora mayúsculas, espacios sobrantes y el tipo de apóstrofo: *Give up* = *give up* = * give   UP *.
- Se comprueba al crear una entrada y al cambiar el término de una existente.
- Si el término ya existe, no se guarda. Se avisa a la usuaria y se ofrece abrir la ficha existente para completarla.
- La regla vale aunque el tipo sea distinto (*record* noun / *record* verb comparten ficha). Términos que solo comparten raíz son distintos: *give* y *give up*.

### 5.2. Temas Cambridge

Etiquetas generales, una o varias por entrada: Work & Economy · Science & Technology · Education · Society & Relationships · Culture & Arts · Travel & Leisure · Health & Wellbeing · Environment · Politics & Law · Global Issues · Food & Nutrition · Crime & Social Issues.

Los temas personalizados se podrán añadir en el futuro; no es prioritario en la V1.

### 5.3. Categorías personales

Agrupaciones propias por significado, concepto o contexto, independientes de los temas: Feelings · Personality · Positive emotions · Negative emotions · Importance · Success & Failure · Improvement & Progress · Communication · Opinions & Arguments · Problems & Solutions · Advantages & Disadvantages · Describing People · Describing Situations · Time & Frequency · Quantity & Degree.

Se puede crear, renombrar, asignar una o varias a una entrada y ver todas sus entradas. Eliminar una categoría pide confirmación y solo retira la asociación, sin borrar entradas.

### 5.4. Sinónimos interactivos

Los sinónimos se enlazan con fichas existentes (p. ej., *Thrilled* → *Elated*, *Excited*, *Overjoyed*; si *Elated* existe, al pulsarlo se abre su ficha). Si el sinónimo no existe, se muestra como texto y, si es sencillo, se ofrece crear la entrada.

- Guardar el texto y, opcionalmente, el ID de la entrada relacionada.
- Buscar coincidencias ignorando mayúsculas y espacios sobrantes.
- No crear duplicados automáticamente.
- Si hay más de una coincidencia, permitir elegir.
- La relación no es simétrica.
- El vínculo por ID sigue funcionando si cambia el término.

```ts
type Synonym = { text: string; entryId?: string };
```

### 5.5. Biblioteca y consulta

Búsqueda por término y significado; filtros por tipo, tema y categoría; orden alfabético y por fecha; lista clara y compacta; acceso a la ficha; edición y eliminación. Se puede explorar por tema o por categoría personal, de forma independiente.

**Ficha:** término, tipo, significado, sinónimos interactivos, antónimos, ejemplo y traducción, temas, categorías, detalles específicos (incluido si es phrasal verb), notas y fecha. No se muestran apartados vacíos.

## 6. Repasar

Flashcards: mostrar el término, revelar el significado con ejemplo y sinónimos, botones **Me cuesta** y **La sé**, tarjeta anterior y siguiente.

Se puede repasar todo, un tema, una categoría o un tipo. Se registra de forma básica si una palabra está aprendida o necesita repaso. Sin repetición espaciada avanzada, calendarios ni gamificación.

## 7. Exámenes

### 7.1. Estructura

Exámenes → Parte → Intento → Contenido del intento.

- **Examen:** nombre (p. ej., *Cambridge C1 · Simulacro 01*), fecha, notas opcionales. Sin límite de exámenes.
- **Partes:** Writing, Speaking, Reading, Use of English, Listening. El C1 oficial tiene cuatro pruebas (Reading & Use of English, Writing, Listening, Speaking). Reading y Use of English se separan solo para organizar el estudio; no se presentan como papers oficiales independientes.
- **Intentos:** varios por parte, con fecha, nombre y notas opcionales. Sin puntuación, duración ni estados.
- **Contenido del intento:**
  - **A. Original:** una o varias fotos; PDF u otros documentos si es viable; transcripción manual opcional; instrucciones; en Writing, tipo de tarea y mínimo/máximo de palabras.
  - **B. Corrección:** fotos o PDF de la corrección del profesor y comentarios opcionales.
  - **C. Versión mejorada:** texto editable, siempre separado del original.
  - **D. Errores:** error, solución, explicación opcional y tipo opcional (Grammar, Vocabulary, Spelling, Collocation, Phrasal verb, Connector, Organisation, Other). Alta manual rápida.

### 7.2. Flujo para Writing

1. Crear intento en Writing.
2. Subir la foto o fotos.
3. Añadir las instrucciones.
4. Indicar el mínimo y el máximo de palabras.
5. Abrir ChatGPT manualmente y adjuntar la foto.
6. Usar el prompt preparado por la aplicación.
7. Copiar el análisis y la versión mejorada.
8. Pegar la versión mejorada en su bloque.
9. Registrar errores y soluciones.
10. Consultar el intento cuando quiera.

Prompt base, con botón para copiarlo (incluyendo tipo de tarea, instrucciones y límites):

> Actúa como profesor especializado en Cambridge C1 Advanced. Analiza el Writing de la imagen adjunta. Primero transcribe fielmente mi texto; si alguna palabra no se entiende, indícalo en lugar de inventarla. Después corrige los errores gramaticales, ortográficos, de vocabulario y colocaciones. Evalúa el texto de forma orientativa según Content, Communicative Achievement, Organisation y Language. A continuación, genera una versión mejorada de nivel C1 que conserve mis ideas y argumentos, pero tenga una estructura más coherente, frases naturales, vocabulario preciso y conectores adecuados. Respeta el tipo de tarea y el límite de palabras indicado. Muestra el recuento de palabras y explica los cambios más importantes. No inventes argumentos ni presentes una calificación como nota oficial de Cambridge.

Sin llamadas a APIs ni automatización de IA.

### 7.3. Biblioteca de errores

Los errores se registran y consultan dentro de cada intento. También hay una vista global con todos los errores, que se puede buscar y filtrar por tipo si no complica la interfaz. Cada error conserva la referencia a su intento. Los errores no se duplican automáticamente en el vocabulario; la usuaria puede crear la entrada a mano.

## 8. Exportación para Claude

Acción visible **Exportar mi preparación C1**, en una pantalla o diálogo sencillo, disponible en cualquier momento.

```
c1-advanced-preparation/
├── README.md
├── vocabulary.md
├── grammar.md
├── expressions-connectors.md
├── personal-categories.md
├── exam-practice.md
├── mistakes.md
├── attempts/<examen>/{writing,speaking,reading,use-of-english,listening}/
├── attachments/…
└── data.json
```

- **README.md:** índice, fecha e instrucciones.
- **vocabulary.md:** término, tipo (con la marca de phrasal verb), significado, ejemplos y sinónimos.
- **grammar.md:** estructuras.
- **expressions-connectors.md:** expresiones y conectores.
- **personal-categories.md:** categorías y sus entradas.
- **exam-practice.md:** índice de exámenes, partes e intentos.
- **mistakes.md:** errores y soluciones.
- **attempts/:** textos originales, correcciones y versiones mejoradas.
- **attachments/:** archivos con nombres que los relacionan con su intento.
- **data.json:** exportación completa con IDs y relaciones.

Los binarios van como archivos separados, nunca dentro de Markdown o JSON. La exportación debe tener contexto suficiente para que Claude sepa de dónde viene cada error e intento.

### 8.3. Importación y copia de seguridad

Exportar una copia completa (datos y archivos), importarla, validarla antes y no sobrescribir datos sin confirmación.

## 9. Tecnología

Local-first, sin backend: React, TypeScript, Vite, Astryx (sujeto a verificación), IndexedDB con Dexie.js, CSS/StyleX según Astryx y PWA opcional. Los datos y los archivos se guardan en IndexedDB (archivos como `Blob`), con IDs estables. No se usa `localStorage` como almacén principal. Los datos están ligados al navegador: hay que avisar de forma discreta de la importancia de las copias y no borrar datos al actualizar.

```
npm install
npm run dev
npm run build
```

## 10. Diseño y experiencia

**Skill obligatoria: `anti-ai-design`.** Antes de diseñar hay que comprobar que está disponible y leerla entera. Si no lo está, se detiene el diseño, se avisa y no se sustituye por otra.

Dirección visual minimalista, clara, profesional y contemporánea, con jerarquía tipográfica, espaciado cómodo y poco color. Bordes discretos, sin exceso de sombras ni tarjetas. Responsive con prioridad móvil, accesible y con navegación por teclado.

Interacciones: formularios breves, campos opcionales diferenciados, confirmación antes de eliminar, estados vacíos útiles, búsqueda rápida, acciones principales visibles y navegación jerárquica clara en Exámenes.

Evitar dashboards complejos, gráficas inútiles, exceso de etiquetas, formularios largos, modales innecesarios, animaciones lentas, IA de pago y sistemas de productividad.

## 11. Modelo de datos

El modelo vigente está en [`src/domain/types.ts`](../src/domain/types.ts). Cambios respecto al orientativo:

- `VocabularyEntry.termKey`: término normalizado con índice único (5.1.1).
- `VocabularyEntry.verb.isPhrasalVerb: boolean`, `false` por defecto.
- Detalles específicos tipados por tipo (`noun`, `verb`, `connector`, `grammar`) en lugar de `Record<string,string>`.
- `Mistake` y `Attachment` en tablas propias, con `attemptId`; cada `Attachment` lleva su bloque (`original` o `correction`).

## 12. Fases

0. Revisión técnica → [FASE-0.md](FASE-0.md)
1. Base visual
2. Vocabulario
3. Repaso
4. Exámenes
5. Exportación y seguridad de datos
6. Pulido

## 13. Criterios de aceptación

**Vocabulario:** crear en segundos; guardar con término y tipo; editar y eliminar; buscar por palabra y significado; filtrar por tipo, tema y categoría; enlazar sinónimos; los vínculos sobreviven a cambios de término; **marcar un verbo como phrasal verb (por defecto estándar)**; **no se puede guardar un término repetido**.

**Repaso:** elegir colección, revelar, marcar aprendida o pendiente y conservar el progreso al cerrar.

**Exámenes:** crear examen con nombre y fecha; entrar en las cinco partes; varios intentos con fechas distintas; adjuntar fotos; guardar corrección y versión mejorada; registrar errores manteniendo el vínculo con su intento.

**Exportación:** exportar todo en un ZIP con Markdown, JSON y adjuntos, conservando relaciones e IDs; importar copia; archivos comprensibles fuera de la app.

**Local y gratuito:** sin cuenta, sin backend, sin APIs de pago, funciona sin conexión, persiste en el navegador y tiene copia de seguridad.

## 14. Decisiones abiertas

Astryx, Dexie, adjuntos, librería ZIP, diseño, estructura interna y PWA. Resueltas en [FASE-0.md](FASE-0.md), salvo el diseño, que está pendiente de la skill. Quedan cerradas: servicios de pago, backend, cuentas, sincronización e IA integrada.

## 15. Instrucciones de trabajo

V1 personal, local y gratuita. Antes de programar: leer la especificación, revisar Astryx y sus versiones, señalar riesgos, proponer la arquitectura y presentar un prototipo navegable; **esperar la validación visual** antes de implementar toda la aplicación. Durante el desarrollo: funcionalidad real, nada de datos simulados como si fueran persistentes, no inventar APIs, justificar dependencias y probar la persistencia y la exportación.
