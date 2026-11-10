import Dexie, { type EntityTable } from "dexie";
import type {
  Attachment, Exam, ExamAttempt, Mistake, PersonalCategory, Topic, VocabularyEntry,
} from "../domain/types";
import { CAMBRIDGE_TOPICS, DEFAULT_CATEGORIES } from "../domain/seeds";

export class C1Database extends Dexie {
  entries!: EntityTable<VocabularyEntry, "id">;
  topics!: EntityTable<Topic, "id">;
  categories!: EntityTable<PersonalCategory, "id">;
  exams!: EntityTable<Exam, "id">;
  attempts!: EntityTable<ExamAttempt, "id">;
  mistakes!: EntityTable<Mistake, "id">;
  attachments!: EntityTable<Attachment, "id">;

  constructor(name = "c1-companion") {
    super(name);
    // &[termKey+type] = índice único: IndexedDB rechaza el mismo término con
    // el mismo tipo. El mismo término con otro tipo sí se permite.
    // Nunca modificar una versión publicada; añadir version(2) con upgrade().
    this.version(1).stores({
      entries: "id, &[termKey+type], termKey, type, *topicIds, *personalCategoryIds, learningStatus, createdAt",
      topics: "id, name",
      categories: "id, name",
      exams: "id, date",
      attempts: "id, examId, [examId+part], date",
      mistakes: "id, attemptId, type",
      attachments: "id, attemptId",
    });
    this.on("populate", (tx) => {
      const now = new Date().toISOString();
      tx.table("topics").bulkAdd(CAMBRIDGE_TOPICS);
      tx.table("categories").bulkAdd(
        DEFAULT_CATEGORIES.map((name) => ({ id: crypto.randomUUID(), name, createdAt: now, updatedAt: now })),
      );
    });
  }
}

export const db = new C1Database();
