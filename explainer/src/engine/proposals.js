/* ═══════════════════════════════════════════════════════════════════════
   Specialist proposal generators — ported from maelstrom/agents.py
   5 specialists × 3 proposals × 5D scores
   ═══════════════════════════════════════════════════════════════════════ */

import { SCORE_DIMS, REGIME_SCORE_WEIGHTS } from './constants.js';

function clamp(v, lo = 0, hi = 1) { return Math.min(hi, Math.max(lo, v)); }

function s(stressorMap, name) { return stressorMap[name] || 0; }

function makeProposal(cycle, phase, specialist, index, description, scores) {
  const clamped = {};
  for (const d of SCORE_DIMS) {
    clamped[d] = Math.round(clamp(scores[d] || 0.5) * 1e6) / 1e6;
  }
  return {
    id: `c${String(cycle).padStart(3, '0')}_${phase}_${specialist}_${index}`,
    cycle, phase, specialist, description, scores: clamped,
  };
}

// ── Kestrel Adar — Evaluate ──────────────────────────────────────────
function kestrelAdar(cycle, sm, rng) {
  const tp = s(sm, 'time_pressure');
  const amb = s(sm, 'ambiguity');
  const threat = s(sm, 'threat_level');
  return [
    makeProposal(cycle, 'evaluate', 'kestrel_adar', 0, 'thorough_assessment', {
      clarity: 0.90 - 0.15 * tp + rng.noise(0.03),
      novelty: 0.15 + rng.noise(0.02),
      defensibility: 0.70 + 0.1 * amb + rng.noise(0.02),
      tempo: 0.25 + 0.15 * tp + rng.noise(0.02),
      coherence: 0.65 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'evaluate', 'kestrel_adar', 1, 'rapid_triage', {
      clarity: 0.55 + 0.1 * threat + rng.noise(0.03),
      novelty: 0.10 + rng.noise(0.02),
      defensibility: 0.40 + rng.noise(0.02),
      tempo: 0.80 + rng.noise(0.02),
      coherence: 0.35 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'evaluate', 'kestrel_adar', 2, 'deep_analysis', {
      clarity: 0.95 + rng.noise(0.02),
      novelty: 0.25 + 0.1 * amb + rng.noise(0.02),
      defensibility: 0.80 + rng.noise(0.02),
      tempo: 0.10 + rng.noise(0.02),
      coherence: 0.80 + rng.noise(0.02),
    }),
  ];
}

// ── Dorian Vale — Generate ───────────────────────────────────────────
function dorianVale(cycle, sm, rng) {
  const opp = s(sm, 'opportunity_pressure');
  const nov = s(sm, 'novelty_pressure');
  const comp = s(sm, 'competition');
  return [
    makeProposal(cycle, 'generate', 'dorian_vale', 0, 'explore_alternatives', {
      clarity: 0.40 + rng.noise(0.03),
      novelty: 0.85 + 0.1 * nov + rng.noise(0.02),
      defensibility: 0.25 + rng.noise(0.02),
      tempo: 0.50 + 0.1 * opp + rng.noise(0.02),
      coherence: 0.30 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'generate', 'dorian_vale', 1, 'conventional_option', {
      clarity: 0.60 + rng.noise(0.03),
      novelty: 0.20 + rng.noise(0.02),
      defensibility: 0.75 + rng.noise(0.02),
      tempo: 0.60 + rng.noise(0.02),
      coherence: 0.65 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'generate', 'dorian_vale', 2, 'creative_synthesis', {
      clarity: 0.35 + rng.noise(0.03),
      novelty: 0.95 + rng.noise(0.02),
      defensibility: 0.20 + 0.1 * comp + rng.noise(0.02),
      tempo: 0.45 + rng.noise(0.02),
      coherence: 0.25 + rng.noise(0.02),
    }),
  ];
}

// ── Helene Quatre — Select ───────────────────────────────────────────
function heleneQuatre(cycle, sm, rng) {
  const mw = s(sm, 'moral_weight');
  const inertia = s(sm, 'institutional_inertia');
  return [
    makeProposal(cycle, 'select', 'helene_quatre', 0, 'defensible_selection', {
      clarity: 0.55 + rng.noise(0.03),
      novelty: 0.10 + rng.noise(0.02),
      defensibility: 0.90 + 0.05 * mw + rng.noise(0.02),
      tempo: 0.35 + rng.noise(0.02),
      coherence: 0.60 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'select', 'helene_quatre', 1, 'pragmatic_choice', {
      clarity: 0.50 + rng.noise(0.03),
      novelty: 0.15 + rng.noise(0.02),
      defensibility: 0.55 + rng.noise(0.02),
      tempo: 0.75 + rng.noise(0.02),
      coherence: 0.50 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'select', 'helene_quatre', 2, 'comprehensive_review', {
      clarity: 0.65 + rng.noise(0.03),
      novelty: 0.05 + rng.noise(0.02),
      defensibility: 0.85 + 0.05 * inertia + rng.noise(0.02),
      tempo: 0.15 + rng.noise(0.02),
      coherence: 0.75 + rng.noise(0.02),
    }),
  ];
}

// ── Vance Calderon — Execute ─────────────────────────────────────────
function vanceCalderon(cycle, sm, rng) {
  const tp = s(sm, 'time_pressure');
  const threat = s(sm, 'threat_level');
  const decay = s(sm, 'resource_decay');
  return [
    makeProposal(cycle, 'execute', 'vance_calderon', 0, 'decisive_action', {
      clarity: 0.45 + rng.noise(0.03),
      novelty: 0.15 + rng.noise(0.02),
      defensibility: 0.40 + rng.noise(0.02),
      tempo: 0.90 + 0.05 * tp + rng.noise(0.02),
      coherence: 0.30 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'execute', 'vance_calderon', 1, 'measured_execution', {
      clarity: 0.55 + rng.noise(0.03),
      novelty: 0.10 + rng.noise(0.02),
      defensibility: 0.65 + 0.1 * threat + rng.noise(0.02),
      tempo: 0.60 + rng.noise(0.02),
      coherence: 0.55 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'execute', 'vance_calderon', 2, 'rapid_deployment', {
      clarity: 0.30 + rng.noise(0.03),
      novelty: 0.20 + rng.noise(0.02),
      defensibility: 0.25 + rng.noise(0.02),
      tempo: 0.95 + rng.noise(0.02),
      coherence: 0.20 - 0.1 * decay + rng.noise(0.02),
    }),
  ];
}

// ── Isolde Marek — Reflect ───────────────────────────────────────────
function isoldeMarek(cycle, sm, rng, regretPrev = 0) {
  const fc = s(sm, 'failure_count');
  const amb = s(sm, 'ambiguity');
  return [
    makeProposal(cycle, 'reflect', 'isolde_marek', 0, 'coherence_review', {
      clarity: 0.55 + rng.noise(0.03),
      novelty: 0.10 + rng.noise(0.02),
      defensibility: 0.60 + rng.noise(0.02),
      tempo: 0.20 + rng.noise(0.02),
      coherence: 0.90 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'reflect', 'isolde_marek', 1, 'blame_attribution', {
      clarity: 0.50 + rng.noise(0.03),
      novelty: 0.05 + rng.noise(0.02),
      defensibility: 0.75 + 0.1 * fc + rng.noise(0.02),
      tempo: 0.15 + rng.noise(0.02),
      coherence: 0.70 + rng.noise(0.02),
    }),
    makeProposal(cycle, 'reflect', 'isolde_marek', 2, 'lesson_extraction', {
      clarity: 0.45 + 0.1 * amb + rng.noise(0.03),
      novelty: 0.30 + 0.15 * regretPrev + rng.noise(0.02),
      defensibility: 0.50 + rng.noise(0.02),
      tempo: 0.10 + rng.noise(0.02),
      coherence: 0.85 + rng.noise(0.02),
    }),
  ];
}

// ── Public API ───────────────────────────────────────────────────────

const GENERATORS = {
  evaluate: kestrelAdar,
  generate: dorianVale,
  select:   heleneQuatre,
  execute:  vanceCalderon,
  reflect:  isoldeMarek,
};

export function generateAllProposals(cycle, stressorMap, rng, regretPrev = 0) {
  const result = {};
  for (const phase of ['evaluate', 'generate', 'select', 'execute', 'reflect']) {
    const gen = GENERATORS[phase];
    result[phase] = phase === 'reflect'
      ? gen(cycle, stressorMap, rng, regretPrev)
      : gen(cycle, stressorMap, rng);
  }
  return result;
}

export function scoreProposalForRegime(proposal, regime) {
  const weights = REGIME_SCORE_WEIGHTS[regime] || REGIME_SCORE_WEIGHTS.peacetime;
  let total = 0;
  for (const d of SCORE_DIMS) {
    total += (weights[d] || 0) * (proposal.scores[d] || 0);
  }
  return total;
}

export function selectBestProposal(proposals, regime) {
  if (!proposals || proposals.length === 0) return null;
  let best = null;
  let bestScore = -Infinity;
  for (const p of proposals) {
    const sc = scoreProposalForRegime(p, regime);
    if (sc > bestScore || (sc === bestScore && (!best || p.id < best.id))) {
      bestScore = sc;
      best = p;
    }
  }
  return best ? { ...best, regimeScore: bestScore } : null;
}
