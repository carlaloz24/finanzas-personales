import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { C1Database } from "../db/db";
import {
  DuplicateTermError, createEntry, deleteCategory, deleteEntry, synonymCandidates, updateEntry,
} from "./vocabulary";

let db: C1Database;
beforeEach(async () => {
  db = new C1Database(`test-${crypto.randomUUID()}`);
  await db.open();
});
afterEach(async () => db.delete());

describe("vocabulario", () => {
  it("guarda con solo término y tipo y siembra temas y categorías", async () => {
    const e = await createEntry(db, { term: "  Thrilled ", type: "adjective" });
    expect(e.term).toBe("Thrilled");
    expect(e.synonyms).toEqual([]);
    expect(await db.topics.count()).toBe(12);
    expect(await db.categories.count()).toBe(15);
  });

  it("no permite introducir el mismo término dos veces", async () => {
    await createEntry(db, { term: "Give up", type: "verb" });
    await expect(createEntry(db, { term: "  give   UP", type: "verb" })).rejects.toBeInstanceOf(DuplicateTermError);
    await expect(createEntry(db, { term: "give up", type: "expression" })).rejects.toBeInstanceOf(DuplicateTermError);
    expect(await db.entries.count()).toBe(1);
  });

  it("el índice único bloquea también escrituras simultáneas", async () => {
    const results = await Promise.allSettled([
      createEntry(db, { term: "elated", type: "adjective" }),
      createEntry(db, { term: "Elated", type: "adjective" }),
    ]);
    expect(results.filter((r) => r.status === "fulfilled")).toHaveLength(1);
    expect(await db.entries.count()).toBe(1);
  });

  it("no permite renombrar una entrada a un término existente, pero sí editarse a sí misma", async () => {
    await createEntry(db, { term: "elated", type: "adjective" });
    const b = await createEntry(db, { term: "overjoyed", type: "adjective" });
    await expect(updateEntry(db, b.id, { term: "Elated", type: "adjective" })).rejects.toBeInstanceOf(DuplicateTermError);
    const same = await updateEntry(db, b.id, { term: "Overjoyed", type: "adjective", meaning: "encantada" });
    expect(same.meaning).toBe("encantada");
  });

  it("un verbo es estándar por defecto y puede marcarse como phrasal verb", async () => {
    const std = await createEntry(db, { term: "rely", type: "verb" });
    expect(std.verb?.isPhrasalVerb).toBe(false);
    const pv = await createEntry(db, { term: "come up with", type: "verb", verb: { isPhrasalVerb: true } });
    expect(pv.verb?.isPhrasalVerb).toBe(true);
    const noun = await createEntry(db, { term: "outcome", type: "noun", verb: { isPhrasalVerb: true } });
    expect(noun.verb).toBeUndefined();
  });

  it("el vínculo de sinónimo sigue funcionando al cambiar el término", async () => {
    const elated = await createEntry(db, { term: "elated", type: "adjective" });
    const [match] = await synonymCandidates(db, " ELATED ");
    const thrilled = await createEntry(db, {
      term: "thrilled", type: "adjective", synonyms: [{ text: "elated", entryId: match.id }, { text: "excited" }],
    });
    await updateEntry(db, elated.id, { term: "Elated (adj.)", type: "adjective" });
    const reloaded = await db.entries.get(thrilled.id);
    expect(reloaded?.synonyms[0].entryId).toBe(elated.id);
    expect((await db.entries.get(elated.id))?.synonyms).toEqual([]); // no simétrico
  });

  it("al borrar una entrada sus vínculos pasan a texto", async () => {
    const elated = await createEntry(db, { term: "elated", type: "adjective" });
    const t = await createEntry(db, { term: "thrilled", type: "adjective", synonyms: [{ text: "elated", entryId: elated.id }] });
    await deleteEntry(db, elated.id);
    expect((await db.entries.get(t.id))?.synonyms).toEqual([{ text: "elated" }]);
  });

  it("borrar una categoría no borra sus entradas", async () => {
    const cat = (await db.categories.toArray())[0];
    const e = await createEntry(db, { term: "upbeat", type: "adjective", personalCategoryIds: [cat.id] });
    await deleteCategory(db, cat.id);
    expect((await db.entries.get(e.id))?.personalCategoryIds).toEqual([]);
  });
});
