import type { SensorValue } from "./logReplayTypes";

type TokenType = "number" | "identifier" | "operator" | "paren" | "comma" | "eof";

interface Token {
  type: TokenType;
  value: string;
}

const FUNCTIONS: Record<string, (...values: number[]) => number> = {
  abs: Math.abs,
  ceil: Math.ceil,
  floor: Math.floor,
  max: Math.max,
  min: Math.min,
  round: Math.round,
  sqrt: Math.sqrt,
};

function tokenize(expression: string): Token[] {
  const tokens: Token[] = [];
  let index = 0;

  while (index < expression.length) {
    const char = expression[index];
    const two = expression.slice(index, index + 2);

    if (/\s/.test(char)) {
      index += 1;
    } else if (/[0-9.]/.test(char)) {
      let value = char;
      index += 1;
      while (index < expression.length && /[0-9.]/.test(expression[index])) {
        value += expression[index];
        index += 1;
      }
      if (!Number.isFinite(Number(value))) throw new Error(`잘못된 숫자입니다: ${value}`);
      tokens.push({ type: "number", value });
    } else if (/[A-Za-z_]/.test(char)) {
      let value = char;
      index += 1;
      while (index < expression.length && /[A-Za-z0-9_]/.test(expression[index])) {
        value += expression[index];
        index += 1;
      }
      tokens.push({ type: "identifier", value });
    } else if (["&&", "||", ">=", "<=", "==", "!="].includes(two)) {
      tokens.push({ type: "operator", value: two });
      index += 2;
    } else if ("+-*/><!".includes(char)) {
      tokens.push({ type: "operator", value: char });
      index += 1;
    } else if ("()".includes(char)) {
      tokens.push({ type: "paren", value: char });
      index += 1;
    } else if (char === ",") {
      tokens.push({ type: "comma", value: char });
      index += 1;
    } else {
      throw new Error(`허용되지 않은 문자입니다: ${char}`);
    }
  }

  tokens.push({ type: "eof", value: "" });
  return tokens;
}

function toNumber(name: string, value: SensorValue | undefined): number {
  if (value === undefined) throw new Error(`알 수 없는 센서입니다: ${name}`);
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

class Parser {
  private index = 0;

  constructor(
    private readonly tokens: Token[],
    private readonly values: Record<string, SensorValue>,
  ) {}

  parse(): number {
    const result = this.or();
    if (this.peek().type !== "eof") throw new Error("수식을 끝까지 해석하지 못했습니다.");
    return Number.isFinite(result) ? result : 0;
  }

  private peek(): Token {
    return this.tokens[this.index];
  }

  private take(value?: string): Token {
    const token = this.peek();
    if (value !== undefined && token.value !== value) throw new Error(`${value}가 필요합니다.`);
    this.index += 1;
    return token;
  }

  private match(...values: string[]): boolean {
    if (!values.includes(this.peek().value)) return false;
    this.index += 1;
    return true;
  }

  private or(): number {
    let left = this.and();
    while (this.match("||")) left = this.and() !== 0 || left !== 0 ? 1 : 0;
    return left;
  }

  private and(): number {
    let left = this.compare();
    while (this.match("&&")) left = this.compare() !== 0 && left !== 0 ? 1 : 0;
    return left;
  }

  private compare(): number {
    let left = this.add();
    while ([">", "<", ">=", "<=", "==", "!="].includes(this.peek().value)) {
      const operator = this.take().value;
      const right = this.add();
      if (operator === ">") left = left > right ? 1 : 0;
      if (operator === "<") left = left < right ? 1 : 0;
      if (operator === ">=") left = left >= right ? 1 : 0;
      if (operator === "<=") left = left <= right ? 1 : 0;
      if (operator === "==") left = left === right ? 1 : 0;
      if (operator === "!=") left = left !== right ? 1 : 0;
    }
    return left;
  }

  private add(): number {
    let left = this.multiply();
    while (["+", "-"].includes(this.peek().value)) {
      const operator = this.take().value;
      const right = this.multiply();
      left = operator === "+" ? left + right : left - right;
    }
    return left;
  }

  private multiply(): number {
    let left = this.unary();
    while (["*", "/"].includes(this.peek().value)) {
      const operator = this.take().value;
      const right = this.unary();
      left = operator === "*" ? left * right : left / right;
    }
    return left;
  }

  private unary(): number {
    if (this.match("-")) return -this.unary();
    if (this.match("+")) return this.unary();
    if (this.match("!")) return this.unary() === 0 ? 1 : 0;
    return this.primary();
  }

  private primary(): number {
    const token = this.peek();
    if (token.type === "number") return Number(this.take().value);
    if (token.type === "identifier") {
      const name = this.take().value;
      if (this.match("(")) {
        const fn = FUNCTIONS[name];
        if (!fn) throw new Error(`허용되지 않은 함수입니다: ${name}`);
        const args: number[] = [];
        if (!this.match(")")) {
          do {
            args.push(this.or());
          } while (this.match(","));
          this.take(")");
        }
        return fn(...args);
      }
      return toNumber(name, this.values[name]);
    }
    if (this.match("(")) {
      const value = this.or();
      this.take(")");
      return value;
    }
    throw new Error(`예상하지 못한 토큰입니다: ${token.value}`);
  }
}

export function evaluateFormula(expression: string, values: Record<string, SensorValue>): number {
  if (/[;[\]{}'"`?]/.test(expression)) throw new Error("허용되지 않은 수식 문법입니다.");
  return new Parser(tokenize(expression), values).parse();
}
