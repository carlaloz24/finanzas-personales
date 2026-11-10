# C1 Companion

App personal y local (sin backend ni cuentas) para preparar Cambridge C1 Advanced.

- Especificación: [docs/ESPECIFICACION.md](docs/ESPECIFICACION.md)
- Revisión técnica y decisiones: [docs/FASE-0.md](docs/FASE-0.md)

## Estado

Hecho: la capa de datos (IndexedDB con Dexie): modelo, temas y categorías
iniciales, vocabulario sin términos repetidos dentro de un mismo tipo, phrasal verbs, sinónimos
enlazados y borrado seguro de categorías.

Pendiente: la interfaz. Espera a la skill `anti-ai-design`.

## Uso

Requiere Node 20 o posterior.

```bash
cd c1-companion
npm install
npm run dev      # servidor local
npm test         # tests de la capa de datos
npm run build    # build de producción en dist/
```

Los datos se guardan en el navegador, en IndexedDB. Si borras los datos del
sitio se pierden, así que exporta copias de seguridad a menudo (la exportación
llega en la Fase 5).
