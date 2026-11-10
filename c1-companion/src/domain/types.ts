// Modelo de datos de la V1. Fechas en ISO 8601 (string) para que la
// exportación JSON sea legible sin conversiones.

export type EntryType =
  | "noun"
  | "verb"
  | "adjective"
  | "adverb"
  | "expression" // agrupa idioms, collocations y expresiones
  | "connector"
  | "grammar-structure";

export type Synonym = {
  text: string;
  /** ID de la entrada enlazada, si existe. El vínculo no es simétrico. */
  entryId?: string;
};

export type Countability = "countable" | "uncountable" | "both";

export type ConnectorFunction =
  | "addition" | "contrast" | "cause" | "consequence" | "example"
  | "conclusion" | "emphasis" | "condition" | "time";

export type ConnectorCategory =
  | "adverb" | "conjunction" | "prepositional-phrase" | "connective-expression";

/** Campos específicos por tipo. Solo se guarda el bloque del tipo elegido. */
export type NounDetails = { countability?: Countability };

export type VerbDetails = {
  /** Casilla opcional del formulario. Sin marcar = verbo estándar. */
  isPhrasalVerb: boolean;
  pastSimple?: string;
  pastParticiple?: string;
  /** Preposición o patrón habitual: "rely on sth", "manage to do". */
  pattern?: string;
};

export type ConnectorDetails = {
  function?: ConnectorFunction;
  category?: ConnectorCategory;
};

export type GrammarDetails = {
  structureName?: string;
  formula?: string;
  usage?: string;
};

export type LearningStatus = "new" | "learning" | "learned";

export type VocabularyEntry = {
  id: string;
  term: string;
  /** Término normalizado; índice único que impide duplicados. */
  termKey: string;
  type: EntryType;
  meaning?: string;
  synonyms: Synonym[];
  antonyms: string[];
  example?: string;
  exampleTranslation?: string;
  topicIds: string[];
  personalCategoryIds: string[];
  notes?: string;
  noun?: NounDetails;
  verb?: VerbDetails;
  connector?: ConnectorDetails;
  grammar?: GrammarDetails;
  learningStatus: LearningStatus;
  createdAt: string;
  updatedAt: string;
};

export type Topic = { id: string; name: string; isCustom: boolean };

export type PersonalCategory = {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
};

export type ExamPart = "writing" | "speaking" | "reading" | "use-of-english" | "listening";

export type Exam = { id: string; name: string; date: string; notes?: string; createdAt: string };

export type MistakeType =
  | "grammar" | "vocabulary" | "spelling" | "collocation"
  | "phrasal-verb" | "connector" | "organisation" | "other";

export type Mistake = {
  id: string;
  attemptId: string;
  original: string;
  correction: string;
  explanation?: string;
  type?: MistakeType;
  createdAt: string;
};

export type AttachmentBlock = "original" | "correction";

export type ExamAttempt = {
  id: string;
  examId: string;
  part: ExamPart;
  date: string;
  name?: string;
  notes?: string;
  instructions?: string;
  writingTaskType?: string;
  minimumWords?: number;
  maximumWords?: number;
  originalText?: string;
  correctionNotes?: string;
  improvedText?: string;
  createdAt: string;
  updatedAt: string;
};

export type Attachment = {
  id: string;
  attemptId: string;
  block: AttachmentBlock;
  fileName: string;
  mimeType: string;
  blob: Blob;
  createdAt: string;
};
