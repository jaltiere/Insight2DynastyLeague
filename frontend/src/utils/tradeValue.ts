/**
 * Trade fairness math for the Trade Calculator.
 *
 * Kept as a pure module (no React) so the verdict logic can be unit tested
 * independently of the page component.
 *
 * Convention: `totalA` / `totalB` are the values each side **sends**. Side A
 * therefore *receives* `totalB`, and vice versa — the winner of a trade is the
 * side that receives more than it gives up.
 */

/**
 * A trade is fair when the larger side is no more than this multiple of the
 * smaller side. 1.10 == "the better half is worth at most 10% more".
 *
 * This replaces an older share-of-total band (±6 percentage points from 50%),
 * which sounded tighter than it was: a 44/56 split is a ratio of 1.273, so the
 * old rule called a trade fair when one side was worth 27% more.
 */
export const FAIR_RATIO = 1.1;

/** Share-of-total bounds equivalent to FAIR_RATIO, for drawing the fair-zone bracket. */
export const FAIR_SHARE_LOW = 1 / (1 + FAIR_RATIO);
export const FAIR_SHARE_HIGH = FAIR_RATIO / (1 + FAIR_RATIO);

export type TradeWinner = 'A' | 'B' | 'even';

export interface TradeVerdict {
  /** Value each side sends. */
  totalA: number;
  totalB: number;
  grandTotal: number;
  /** Value each side receives (A receives what B sends). */
  receivedA: number;
  receivedB: number;
  /** Share of all value on the table that each side *receives*. Sums to 1. */
  shareA: number;
  shareB: number;
  /** Absolute difference between the two sides. */
  gap: number;
  /** Gap as a percentage of the smaller side — null when a side is empty. */
  gapPct: number | null;
  /** Larger side divided by smaller side. Infinity when a side is empty. */
  ratio: number;
  isFair: boolean;
  /** Side receiving more value. 'even' only when the sides are exactly equal. */
  winner: TradeWinner;
}

export function evaluateTrade(totalA: number, totalB: number): TradeVerdict {
  const grandTotal = totalA + totalB;
  const gap = Math.abs(totalA - totalB);
  const hi = Math.max(totalA, totalB);
  const lo = Math.min(totalA, totalB);

  const ratio = lo > 0 ? hi / lo : hi > 0 ? Infinity : 1;
  const gapPct = lo > 0 ? Math.round((gap / lo) * 100) : null;

  // A receives what B sends, so A's share of received value is totalB / total.
  const receivedA = totalB;
  const receivedB = totalA;
  const shareA = grandTotal > 0 ? receivedA / grandTotal : 0.5;

  return {
    totalA,
    totalB,
    grandTotal,
    receivedA,
    receivedB,
    shareA,
    shareB: 1 - shareA,
    gap,
    gapPct,
    ratio,
    isFair: ratio <= FAIR_RATIO,
    winner: gap === 0 ? 'even' : receivedA > receivedB ? 'A' : 'B',
  };
}
