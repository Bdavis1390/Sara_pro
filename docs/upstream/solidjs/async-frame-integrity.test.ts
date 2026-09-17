import { describe, expect, it } from "vitest";
import {
  createMemo,
  createRenderEffect,
  createRoot,
  createSignal,
  flush,
  isPending
} from "../src/index.js";

// Deterministic manual clock. This mirrors the existing async-chain and
// held-conditional tests: promise resolutions are ordered by due time and
// each landing gets a full microtask + Solid flush drain.
let now = 0;
let timers: { at: number; run: () => void }[] = [];

function delay<T>(ms: number, value?: T): Promise<T> {
  return new Promise<T>(resolve =>
    timers.push({ at: now + ms, run: () => resolve(value as T) })
  );
}

async function settle() {
  for (let round = 0; round < 3; round++) {
    for (let i = 0; i < 10; i++) await Promise.resolve();
    flush();
  }
}

async function advanceTo(t: number) {
  while (true) {
    timers.sort((a, b) => a.at - b.at);
    const next = timers[0];
    if (!next || next.at > t) break;
    timers.shift();
    now = next.at;
    next.run();
    await settle();
  }
  now = t;
  await settle();
}

function reset() {
  now = 0;
  timers = [];
}

function frames(log: string[], when: number[]): string[] {
  const byTime = new Map<number, string[]>();
  log.forEach((value, i) =>
    (byTime.get(when[i]) ?? byTime.set(when[i], []).get(when[i])!).push(value)
  );
  return [...byTime].map(([t, values]) => `${t}: ${values.sort().join(" | ")}`);
}

function text(fn: () => string, log: string[], when: number[]) {
  let last: string | undefined;
  createRenderEffect(fn, value => {
    if (value !== last) {
      last = value;
      log.push(value);
      when.push(now);
    }
  });
}

describe("async frame integrity — cross-rule interleavings", () => {
  it("A29 × isPending: late tracked readers join the hold while probes remain observable", async () => {
    reset();
    const log: string[] = [];
    const when: number[] = [];

    let setCount!: (v: number) => void;
    let setShowA!: (v: boolean) => void;
    let setShowB!: (v: boolean) => void;

    createRoot(() => {
      const [count, sc] = createSignal(0);
      const [showA, sA] = createSignal(false);
      const [showB, sB] = createSignal(false);
      setCount = sc;
      setShowA = sA;
      setShowB = sB;

      const details = createMemo(() => delay(1000, count()));
      const panelA = createMemo(() => (showA() ? count() : "hidden"));
      const panelB = createMemo(() => (showB() ? count() : "hidden"));

      text(() => `Count: ${count()}`, log, when);
      text(() => `Details: ${details()}`, log, when);
      text(() => `PanelA: ${panelA()}`, log, when);
      text(() => `PanelB: ${panelB()}`, log, when);
      text(() => `Pending: ${isPending(count)}`, log, when);
    });

    flush();
    await settle();
    await advanceTo(2000);

    setCount(1);
    await settle();

    await advanceTo(2300);
    setShowA(true);
    await settle();

    await advanceTo(2600);
    setShowB(true);
    await settle();

    await advanceTo(4000);

    expect(frames(log, when)).toEqual([
      "0: Count: 0 | PanelA: hidden | PanelB: hidden | Pending: false",
      "1000: Details: 0",
      "2000: Pending: true",
      "3000: Count: 1 | Details: 1 | PanelA: 1 | PanelB: 1 | Pending: false"
    ]);
  });

  it("A30 × stale landing: both old and newly staged dependencies stay frame-coherent until replacement commits", async () => {
    reset();
    const log: string[] = [];
    const when: number[] = [];

    let setA!: (v: number) => void;
    let setB!: (v: number) => void;
    let setUseB!: (v: boolean) => void;

    createRoot(() => {
      const [a, sa] = createSignal(0);
      const [b, sb] = createSignal(10);
      const [useB, su] = createSignal(false);
      setA = sa;
      setB = sb;
      setUseB = su;

      const selected = createMemo(() => (useB() ? b() : a()));
      const details = createMemo(() => delay(1000, selected()));

      text(() => `A: ${a()}`, log, when);
      text(() => `B: ${b()}`, log, when);
      text(() => `UseB: ${useB()}`, log, when);
      text(() => `Selected: ${selected()}`, log, when);
      text(() => `Details: ${details()}`, log, when);
    });

    flush();
    await settle();
    await advanceTo(2000);

    setUseB(true);
    await settle();

    await advanceTo(2250);
    setA(1);
    await settle();

    await advanceTo(2500);
    setB(11);
    await settle();

    await advanceTo(5000);

    expect(frames(log, when)).toEqual([
      "0: A: 0 | B: 10 | Selected: 0 | UseB: false",
      "1000: Details: 0",
      "3500: A: 1 | B: 11 | Details: 11 | Selected: 11 | UseB: true"
    ]);
  });

  it("A29 × A30: a late reader of a dependency-switched memo cannot escape the staged frame", async () => {
    reset();
    const log: string[] = [];
    const when: number[] = [];

    let setPrimary!: (v: number) => void;
    let setAlternate!: (v: number) => void;
    let setUseAlternate!: (v: boolean) => void;
    let setShow!: (v: boolean) => void;

    createRoot(() => {
      const [primary, sp] = createSignal(0);
      const [alternate, sa] = createSignal(10);
      const [useAlternate, su] = createSignal(false);
      const [show, ss] = createSignal(false);
      setPrimary = sp;
      setAlternate = sa;
      setUseAlternate = su;
      setShow = ss;

      const selected = createMemo(() => (useAlternate() ? alternate() : primary()));
      const details = createMemo(() => delay(1000, selected()));
      const panel = createMemo(() => (show() ? selected() : "hidden"));

      text(() => `Primary: ${primary()}`, log, when);
      text(() => `Alternate: ${alternate()}`, log, when);
      text(() => `UseAlternate: ${useAlternate()}`, log, when);
      text(() => `Selected: ${selected()}`, log, when);
      text(() => `Details: ${details()}`, log, when);
      text(() => `Panel: ${panel()}`, log, when);
    });

    flush();
    await settle();
    await advanceTo(2000);

    setUseAlternate(true);
    await settle();

    await advanceTo(2250);
    setPrimary(1);
    await settle();

    await advanceTo(2500);
    setShow(true);
    await settle();

    await advanceTo(2600);
    setAlternate(11);
    await settle();

    await advanceTo(5000);

    expect(frames(log, when)).toEqual([
      "0: Alternate: 10 | Panel: hidden | Primary: 0 | Selected: 0 | UseAlternate: false",
      "1000: Details: 0",
      "3600: Alternate: 11 | Details: 11 | Panel: 11 | Primary: 1 | Selected: 11 | UseAlternate: true"
    ]);
  });
});
