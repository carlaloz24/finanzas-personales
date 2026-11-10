/**
 * Clave de comparación de términos: ignora mayúsculas, espacios sobrantes
 * y tipografía de apóstrofos. "  Give  UP " y "give up" son el mismo término.
 */
export function termKey(term: string): string {
  return term
    .normalize("NFC")
    .replace(/[‘’ʼ]/g, "'")
    .trim()
    .replace(/\s+/g, " ")
    .toLocaleLowerCase("en");
}
