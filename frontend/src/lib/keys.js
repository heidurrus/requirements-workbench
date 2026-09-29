// Shortcuts by physical key: A / X / E / J / K must work while the Russian layout is on,
// where e.key is "ф", "ч", "у"… Letters, digits and brackets come from e.code.
const CODES = { BracketLeft: "[", BracketRight: "]", Slash: "/", Backslash: "\\", Comma: ",", Space: " " };

export function keyOf(e) {
  const c = e.code || "";
  if (/^Key[A-Z]$/.test(c)) return c.slice(3).toLowerCase();
  if (/^Digit\d$/.test(c)) return c.slice(5);
  if (CODES[c] !== undefined) return CODES[c];
  return e.key;
}
