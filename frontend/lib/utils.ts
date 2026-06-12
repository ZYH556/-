type ClassNameValue = string | number | false | null | undefined

export function cn(...values: ClassNameValue[]): string {
  return values.filter(Boolean).join(" ")
}
