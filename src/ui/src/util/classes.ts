const consecutiveSpace = / {2,}/;

export function stripClassWhitespace(classString: string): string {
  return classString.replace(consecutiveSpace, " ").trim();
}

// filter out falsy classes
export default function classes(...args: (string | false | null)[]): string {
  return args.filter((cls) => !!cls).join(" ");
}
