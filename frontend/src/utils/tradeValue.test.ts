import { describe, it, expect } from 'vitest';
import { evaluateTrade, FAIR_RATIO, FAIR_SHARE_LOW, FAIR_SHARE_HIGH } from './tradeValue';

// Real KTC values from the Reed/Tuten trade that exposed both bugs.
const REED = 4215;
const TUTEN = 5055;

describe('evaluateTrade — winner orientation', () => {
  it('names the side that receives more, not the side that sends more', () => {
    // Side A sends Reed (4215), side B sends Tuten (5055).
    // A receives the more valuable player, so A wins.
    const v = evaluateTrade(REED, TUTEN);
    expect(v.winner).toBe('A');
    expect(v.receivedA).toBe(TUTEN);
    expect(v.receivedB).toBe(REED);
  });

  it('is symmetric when the sides are swapped', () => {
    expect(evaluateTrade(TUTEN, REED).winner).toBe('B');
  });

  it('reports even only when the sides are exactly equal', () => {
    expect(evaluateTrade(5000, 5000).winner).toBe('even');
    expect(evaluateTrade(5000, 5001).winner).toBe('A');
  });

  it('gives the winner the larger share of received value', () => {
    const v = evaluateTrade(REED, TUTEN);
    expect(v.shareA).toBeGreaterThan(0.5);
    expect(v.shareA + v.shareB).toBeCloseTo(1);
  });
});

describe('evaluateTrade — fair zone', () => {
  it('rejects the Reed/Tuten trade that the old ±6% share band accepted', () => {
    const v = evaluateTrade(REED, TUTEN);
    expect(v.isFair).toBe(false);
    expect(v.gap).toBe(840);
    // 5055 / 4215 = 1.199 — a 20% overpay.
    expect(v.gapPct).toBe(20);
    expect(v.ratio).toBeCloseTo(1.199, 3);
  });

  it('accepts a trade inside the ratio threshold', () => {
    const v = evaluateTrade(5000, 5400); // ratio 1.08
    expect(v.isFair).toBe(true);
    expect(v.gapPct).toBe(8);
  });

  it('treats exactly FAIR_RATIO as fair and just past it as unfair', () => {
    expect(evaluateTrade(1000, 1000 * FAIR_RATIO).isFair).toBe(true);
    expect(evaluateTrade(1000, 1000 * FAIR_RATIO + 1).isFair).toBe(false);
  });

  it('no longer tolerates the 27% gap the old 44/56 share band allowed', () => {
    // 44/56 of a 10,000-point trade — fair under the old rule, not under this one.
    const v = evaluateTrade(4400, 5600);
    expect(v.isFair).toBe(false);
    expect(v.gapPct).toBe(27);
  });

  it('applies the same threshold regardless of trade size', () => {
    // The old share-based band widened in absolute terms as the trade grew;
    // a ratio threshold does not.
    expect(evaluateTrade(1000, 1150).isFair).toBe(false);
    expect(evaluateTrade(10000, 11500).isFair).toBe(false);
    expect(evaluateTrade(1000, 1050).isFair).toBe(true);
    expect(evaluateTrade(10000, 10500).isFair).toBe(true);
  });
});

describe('evaluateTrade — edge cases', () => {
  it('treats a one-sided trade as unfair with no percentage', () => {
    const v = evaluateTrade(0, TUTEN);
    expect(v.isFair).toBe(false);
    expect(v.winner).toBe('A');
    expect(v.ratio).toBe(Infinity);
    expect(v.gapPct).toBeNull();
  });

  it('handles an empty trade without dividing by zero', () => {
    const v = evaluateTrade(0, 0);
    expect(v.winner).toBe('even');
    expect(v.isFair).toBe(true);
    expect(v.shareA).toBe(0.5);
    expect(v.gapPct).toBe(null);
  });
});

describe('fair zone bracket bounds', () => {
  it('derives share bounds that match the ratio threshold', () => {
    expect(FAIR_SHARE_LOW + FAIR_SHARE_HIGH).toBeCloseTo(1);
    expect(FAIR_SHARE_HIGH / FAIR_SHARE_LOW).toBeCloseTo(FAIR_RATIO);
    // ~47.6% / ~52.4%, noticeably tighter than the old 44% / 56%.
    expect(FAIR_SHARE_LOW).toBeCloseTo(0.4762, 4);
    expect(FAIR_SHARE_HIGH).toBeCloseTo(0.5238, 4);
  });

  it('agrees with evaluateTrade at the boundary', () => {
    const v = evaluateTrade(1000, 1000 * FAIR_RATIO);
    expect(v.shareA).toBeCloseTo(FAIR_SHARE_HIGH, 6);
  });
});
