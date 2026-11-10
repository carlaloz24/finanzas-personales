import type { Topic } from "./types";

export const CAMBRIDGE_TOPICS: Topic[] = [
  "Work & Economy", "Science & Technology", "Education", "Society & Relationships",
  "Culture & Arts", "Travel & Leisure", "Health & Wellbeing", "Environment",
  "Politics & Law", "Global Issues", "Food & Nutrition", "Crime & Social Issues",
].map((name, i) => ({ id: `topic-${String(i + 1).padStart(2, "0")}`, name, isCustom: false }));

export const DEFAULT_CATEGORIES: string[] = [
  "Feelings", "Personality", "Positive emotions", "Negative emotions", "Importance",
  "Success & Failure", "Improvement & Progress", "Communication", "Opinions & Arguments",
  "Problems & Solutions", "Advantages & Disadvantages", "Describing People",
  "Describing Situations", "Time & Frequency", "Quantity & Degree",
];
