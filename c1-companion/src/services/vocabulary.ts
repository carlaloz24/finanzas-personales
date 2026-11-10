import Dexie from "dexie";
import type { C1Database } from "../db/db";
import { termKey } from "../domain/normalize";
import type {
  ConnectorDetails, EntryType, GrammarDetails, NounDetails, Synonym, VerbDetails, VocabularyEntry,
} from "../domain/types";

export class DuplicateTermError extends Error {
  constructor(public readonly existing: VocabularyEntry) {
    super(`«${existing.term}» (${existing.type}) ya está en tu vocabulario.`);
    this.name = "DuplicateTermError";
  }
}

export type EntryInput = {
  term: string;
  type: EntryType;
  meaning?: string;
  synonyms?: Synonym[];
  antonyms?: string[];
  example?: string;
  exampleTranslation?: string;
  topicIds?: string[];
  personalCategoryIds?: string[];
  notes?: string;
  noun?: NounDetails;
  verb?: Partial<VerbDetails>;
  connector?: ConnectorDetails;
  grammar?: GrammarDetails;
};

const blank = (s?: string) => {
  const t = s?.trim();
  return t ? t : undefined;
};

/** Conserva solo los campos específicos del tipo elegido. */
function typeDetails(input: EntryInput): Pick<VocabularyEntry, "noun" | "verb" | "connector" | "grammar"> {
  switch (input.type) {
    case "noun": return { noun: { ...input.noun } };
    case "verb": return { verb: { ...input.verb, isPhrasalVerb: input.verb?.isPhrasalVerb ?? false } };
    case "connector": return { connector: { ...input.connector } };
    case "grammar-structure": return { grammar: { ...input.grammar } };
    default: return {};
  }
}

function build(input: EntryInput): Omit<VocabularyEntry, "id" | "createdAt" | "updatedAt" | "learningStatus"> {
  const term = input.term.trim().replace(/\s+/g, " ");
  if (!term) throw new Error("El término es obligatorio.");
  return {
    term,
    termKey: termKey(term),
    type: input.type,
    meaning: blank(input.meaning),
    synonyms: (input.synonyms ?? []).filter((s) => s.text.trim()).map((s) => ({ ...s, text: s.text.trim() })),
    antonyms: (input.antonyms ?? []).map((a) => a.trim()).filter(Boolean),
    example: blank(input.example),
    exampleTranslation: blank(input.exampleTranslation),
    topicIds: input.topicIds ?? [],
    personalCategoryIds: input.personalCategoryIds ?? [],
    notes: blank(input.notes),
    ...typeDetails(input),
  };
}

/** Todas las entradas con ese término, de cualquier tipo. */
export function findByTerm(db: C1Database, term: string) {
  return db.entries.where("termKey").equals(termKey(term)).toArray();
}

/** La entrada con ese término y ese tipo, si existe. */
export function findByTermAndType(db: C1Database, term: string, type: EntryType) {
  return db.entries.where("[termKey+type]").equals([termKey(term), type]).first();
}

async function guardUnique(db: C1Database, key: string, type: EntryType, selfId?: string) {
  const existing = await db.entries.where("[termKey+type]").equals([key, type]).first();
  if (existing && existing.id !== selfId) throw new DuplicateTermError(existing);
}

/** Si dos escrituras compiten, el índice único de IndexedDB hace de red de seguridad. */
async function rethrowConstraint(db: C1Database, key: string, type: EntryType, err: unknown): Promise<never> {
  if (err instanceof Dexie.ConstraintError || (err as Error)?.name === "ConstraintError") {
    const existing = await db.entries.where("[termKey+type]").equals([key, type]).first();
    if (existing) throw new DuplicateTermError(existing);
  }
  throw err;
}

export async function createEntry(db: C1Database, input: EntryInput): Promise<VocabularyEntry> {
  const data = build(input);
  await guardUnique(db, data.termKey, data.type);
  const now = new Date().toISOString();
  const entry: VocabularyEntry = {
    ...data, id: crypto.randomUUID(), learningStatus: "new", createdAt: now, updatedAt: now,
  };
  try {
    await db.entries.add(entry);
  } catch (err) {
    return rethrowConstraint(db, data.termKey, data.type, err);
  }
  return entry;
}

export async function updateEntry(db: C1Database, id: string, input: EntryInput): Promise<VocabularyEntry> {
  const current = await db.entries.get(id);
  if (!current) throw new Error("La entrada no existe.");
  const data = build(input);
  await guardUnique(db, data.termKey, data.type, id);
  // Se reemplaza el registro completo para descartar campos de un tipo anterior.
  const entry: VocabularyEntry = {
    ...data,
    id,
    learningStatus: current.learningStatus,
    createdAt: current.createdAt,
    updatedAt: new Date().toISOString(),
  };
  try {
    await db.entries.put(entry);
  } catch (err) {
    return rethrowConstraint(db, data.termKey, data.type, err);
  }
  return entry;
}

/** Elimina la entrada y retira los vínculos de sinónimos que apuntaban a ella (el texto se conserva). */
export async function deleteEntry(db: C1Database, id: string) {
  await db.transaction("rw", db.entries, async () => {
    await db.entries.delete(id);
    await db.entries
      .filter((e) => e.synonyms.some((s) => s.entryId === id))
      .modify((e) => {
        e.synonyms = e.synonyms.map((s) => (s.entryId === id ? { text: s.text } : s));
      });
  });
}

/**
 * Candidatas para enlazar un sinónimo. Puede haber varias (mismo término con
 * distinto tipo); la interfaz deja elegir cuál enlazar.
 */
export async function synonymCandidates(db: C1Database, text: string, excludeId?: string) {
  return (await findByTerm(db, text)).filter((e) => e.id !== excludeId);
}

export async function setLearningStatus(db: C1Database, id: string, status: VocabularyEntry["learningStatus"]) {
  await db.entries.update(id, { learningStatus: status });
}

/** Borra la categoría y solo retira la asociación de las entradas. */
export async function deleteCategory(db: C1Database, categoryId: string) {
  await db.transaction("rw", db.categories, db.entries, async () => {
    await db.categories.delete(categoryId);
    await db.entries.where("personalCategoryIds").equals(categoryId).modify((e) => {
      e.personalCategoryIds = e.personalCategoryIds.filter((c) => c !== categoryId);
    });
  });
}
