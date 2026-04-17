/* ═══════════════════════════════════════════════════════════════════════
   SimulationEngine — Client-side Maelstrom runtime
   Faithful port of the 5-phase cycle computation pipeline.
   All visuals subscribe to state changes.
   ═══════════════════════════════════════════════════════════════════════ */

import { DeterministicRNG } from './rng.js';
import {
  STRESSOR_NAMES, STRESSOR_SCHEDULE, DEMO_CYCLES,
  TRANSITIONS, REGIME_WEIGHTS, REGIME_INERTIA, GRADIENT_WINDOW,
  REGIME_IDS, REGIME_PRIORITY, PHASES, BYPASSES, BYPASS_REPLACES,
} from './constants.js';
import { generateAllProposals, scoreProposalForRegime, selectBestProposal } from './proposals.js';

// ── Helpers ──────────────────────────────────────────────────────────

function dot(a, b) {
  let sum = 0;
  for (let i = 0; i < a.length && i < b.length; i++) sum += a[i] * b[i];
  return sum;
}

function interpolate(schedule, t) {
  if (!schedule || schedule.length === 0) return 0;
  if (t <= schedule[0][0]) return schedule[0][1];
  if (t >= schedule[schedule.length - 1][0]) return schedule[schedule.length - 1][1];
  for (let i = 0; i < schedule.length - 1; i++) {
    const [t0, v0] = schedule[i];
    const [t1, v1] = schedule[i + 1];
    if (t >= t0 && t <= t1) {
      const frac = (t - t0) / (t1 - t0);
      return v0 + frac * (v1 - v0);
    }
  }
  return schedule[schedule.length - 1][1];
}

function hashState(obj) {
  // Simple deterministic hash for demo (not crypto-grade)
  const str = JSON.stringify(obj);
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h + str.charCodeAt(i)) | 0;
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

// ── SimulationEngine ─────────────────────────────────────────────────

export class SimulationEngine {
  constructor() {
    this.totalCycles = DEMO_CYCLES;
    this.seed = 42;
    this.currentCycle = 1;
    this.stressorOverrides = {};  // user slider values override schedule
    this.subscribers = [];
    this.state = null;
    this.fullTrace = [];
    this._suppressNotify = false;
  }

  // ── Subscription ────────────────────────────────────────────────
  subscribe(fn) { this.subscribers.push(fn); }

  _notify() {
    if (this._suppressNotify) return;
    for (const fn of this.subscribers) fn(this.state);
  }

  getState() { return this.state; }
  getFullTrace() { return this.fullTrace; }

  // ── Input methods ───────────────────────────────────────────────
  setStressor(name, value) {
    this.stressorOverrides[name] = value;
    this.computeCurrentCycle();
    this.runFullSimulation();
    this._notify();
  }

  setStressors(map) {
    Object.assign(this.stressorOverrides, map);
    this.computeCurrentCycle();
    this.runFullSimulation();
    this._notify();
  }

  setCycle(t) {
    this.currentCycle = Math.max(1, Math.min(this.totalCycles, t));
    this.computeCurrentCycle();
    this._notify();
  }

  setSeed(seed) {
    this.seed = seed;
    this.computeCurrentCycle();
    this.runFullSimulation();
    this._notify();
  }

  // ── Stressor interpolation ──────────────────────────────────────
  _getStressorVector(t) {
    const vec = [];
    const map = {};
    for (const name of STRESSOR_NAMES) {
      let val;
      if (name in this.stressorOverrides) {
        val = this.stressorOverrides[name];
      } else {
        val = interpolate(STRESSOR_SCHEDULE[name] || [], t);
      }
      vec.push(val);
      map[name] = val;
    }
    return { vec, map };
  }

  // ── Legality deformation ────────────────────────────────────────
  _deformLegality(stressorVec) {
    const result = {};
    for (const tr of TRANSITIONS) {
      const key = `${tr.source}->${tr.target}`;
      const aPrime = tr.A - dot(tr.alpha, stressorVec);
      const wPrime = Math.max(0, tr.W + dot(tr.beta, stressorVec));
      result[key] = {
        source: tr.source, target: tr.target,
        A_prime: aPrime, W_prime: wPrime,
        admissible: aPrime > 0,
        alpha: tr.alpha, beta: tr.beta, A: tr.A, W: tr.W,
      };
    }
    return result;
  }

  // ── Penalty signals ─────────────────────────────────────────────
  _computePenalties(stressorVec, constraintState) {
    const result = {};
    for (const r of REGIME_IDS) {
      const rw = REGIME_WEIGHTS[r];
      result[r] = dot(rw.w, stressorVec) + dot(rw.u, constraintState);
    }
    return result;
  }

  // ── Gradients ───────────────────────────────────────────────────
  _computeGradients(currentPenalties, penaltyHistory) {
    if (penaltyHistory.length === 0) {
      return { ...currentPenalties };
    }
    const lookback = Math.min(GRADIENT_WINDOW, penaltyHistory.length);
    const past = penaltyHistory[penaltyHistory.length - lookback];
    const grads = {};
    for (const r of REGIME_IDS) {
      grads[r] = (currentPenalties[r] - (past[r] || 0)) / lookback;
    }
    return grads;
  }

  // ── Regime selection with inertia ───────────────────────────────
  _selectRegime(gradients, prevRegime) {
    const adjusted = { ...gradients };

    // Out-of bonus for current regime (stickiness)
    if (prevRegime) {
      const outBonus = REGIME_INERTIA[`out_of_${prevRegime}`] || REGIME_INERTIA.default || 0;
      adjusted[prevRegime] = (adjusted[prevRegime] || 0) + outBonus;
    }

    // Into penalty for challengers
    for (const r of REGIME_IDS) {
      if (r !== prevRegime) {
        const intoPenalty = REGIME_INERTIA[`into_${r}`] || 0;
        if (intoPenalty > 0) adjusted[r] = (adjusted[r] || 0) - intoPenalty;
      }
    }

    // Argmax with deterministic tie-break
    let best = null;
    let bestVal = -Infinity;
    for (const r of REGIME_IDS) {
      const val = adjusted[r] || 0;
      const priority = REGIME_PRIORITY.indexOf(r);
      if (val > bestVal || (val === bestVal && priority < (REGIME_PRIORITY.indexOf(best) ?? 999))) {
        bestVal = val;
        best = r;
      }
    }
    return best || 'peacetime';
  }

  // ── Bypass eligibility ──────────────────────────────────────────
  _evaluateBypassEligibility(activeRegime, stressorMap, deformed) {
    const results = {};
    for (const bp of BYPASSES) {
      const regimeOk = bp.eligibleRegimes.includes(activeRegime);
      let intensity = 0;
      for (const [sName, weight] of Object.entries(bp.stressorWeights)) {
        intensity += weight * (stressorMap[sName] || 0);
      }
      const budget = bp.latencyBudget[activeRegime] || 1.0;
      const exceedsBudget = intensity > budget;
      const tKey = `${bp.sourcePhase}->${bp.targetPhase}`;
      const dt = deformed[tKey];
      const transitionAdmissible = dt ? dt.admissible : false;
      const eligible = regimeOk && exceedsBudget && transitionAdmissible;

      // Penalty saving
      const bypassPenalty = dt ? dt.W_prime : Infinity;
      const replacedKeys = BYPASS_REPLACES[bp.name] || [];
      let canonicalSubPenalty = 0;
      for (const k of replacedKeys) {
        if (deformed[k]) canonicalSubPenalty += deformed[k].W_prime;
      }
      const penaltySaving = replacedKeys.length > 0
        ? canonicalSubPenalty - bypassPenalty
        : (exceedsBudget ? intensity - budget : 0);

      results[bp.name] = {
        name: bp.name, eligible, regimeOk, intensity,
        budget, exceedsBudget, transitionAdmissible,
        penaltySaving, regime: activeRegime,
      };
    }
    return results;
  }

  // ── Single cycle computation ────────────────────────────────────
  computeCurrentCycle() {
    const t = this.currentCycle;
    const rng = new DeterministicRNG(this.seed);

    // We need to advance the RNG to the correct state for cycle t
    // by running all previous cycles first (deterministic!)
    let prevRegime = null;
    let penaltyHistory = [];
    let constraintState = [0, 0, 0, 0, 0, 0]; // 6 floats
    let prevRegret = 0;

    let finalState = null;

    for (let c = 1; c <= t; c++) {
      const { vec: stressorVec, map: stressorMap } = this._getStressorVector(c);
      const deformed = this._deformLegality(stressorVec);
      const penalties = this._computePenalties(stressorVec, constraintState);
      const gradients = this._computeGradients(penalties, penaltyHistory);
      const activeRegime = this._selectRegime(gradients, prevRegime);
      const regimeChanged = prevRegime !== null && activeRegime !== prevRegime;

      const proposals = generateAllProposals(c, stressorMap, rng, prevRegret);
      const bypassEligibility = this._evaluateBypassEligibility(activeRegime, stressorMap, deformed);

      // Select best eligible bypass
      let activatedBypass = null;
      let bestSaving = 0;
      for (const [name, be] of Object.entries(bypassEligibility)) {
        if (be.eligible && be.penaltySaving > bestSaving) {
          bestSaving = be.penaltySaving;
          activatedBypass = name;
        }
      }

      // Determine execution path
      let executionPath = [...PHASES];
      if (activatedBypass) {
        const bp = BYPASSES.find(b => b.name === activatedBypass);
        if (bp) executionPath = [...bp.collapsedPath];
      }

      // Select best proposal per executed phase
      const selectedProposals = {};
      let executedValue = 0;
      const seen = new Set();
      for (const phase of executionPath) {
        if (seen.has(phase)) continue;
        seen.add(phase);
        const best = selectBestProposal(proposals[phase] || [], activeRegime);
        selectedProposals[phase] = best;
        if (phase === 'execute' && best) {
          executedValue = best.regimeScore;
        }
      }

      // Compute counterfactual best
      let counterfactualBest = 0;
      for (const phase of PHASES) {
        for (const p of (proposals[phase] || [])) {
          const sc = scoreProposalForRegime(p, activeRegime);
          if (sc > counterfactualBest) counterfactualBest = sc;
        }
      }
      const regret = Math.max(0, counterfactualBest - executedValue);

      // Canonical path admissible?
      const canonicalKeys = [
        'evaluate->generate', 'generate->select', 'select->execute',
        'execute->reflect', 'reflect->evaluate',
      ];
      const canonicalAdmissible = canonicalKeys.every(k => deformed[k] && deformed[k].admissible);
      let canonicalPenalty = 0;
      for (const k of canonicalKeys) {
        if (deformed[k]) canonicalPenalty += deformed[k].W_prime;
      }

      // State hash
      const stateHash = hashState({
        cycle: c, stressorVec, activeRegime,
        executedValue: Math.round(executedValue * 1e6) / 1e6,
        rngDraws: rng.drawCount,
      });

      finalState = {
        cycle: c,
        stressorVector: stressorMap,
        stressorVec,
        legality: deformed,
        penalties,
        gradients,
        activeRegime,
        regimeChanged,
        proposals,
        selectedProposals,
        executionPath,
        bypassEligibility,
        activatedBypass,
        executedValue,
        counterfactualBest,
        regret,
        canonicalAdmissible,
        canonicalPenalty,
        stateHash,
      };

      // Update state for next cycle
      const decay = 0.8;
      const bpActivated = activatedBypass !== null;
      constraintState = [
        constraintState[0] * decay + (canonicalAdmissible ? 0 : 1),
        constraintState[1] * decay, // identity veto (simplified)
        constraintState[2] * decay, // coalition veto (simplified)
        0, // coalition drag
        constraintState[4] * decay + (bpActivated ? 1 : 0),
        regimeChanged ? 0 : constraintState[5] + 1,
      ];
      penaltyHistory.push(penalties);
      prevRegime = activeRegime;
      prevRegret = regret;
    }

    this.state = finalState;
    return finalState;
  }

  // ── Full simulation (all cycles) ────────────────────────────────
  runFullSimulation() {
    const savedCycle = this.currentCycle;
    this._suppressNotify = true;
    this.fullTrace = [];

    for (let t = 1; t <= this.totalCycles; t++) {
      this.currentCycle = t;
      const state = this.computeCurrentCycle();
      this.fullTrace.push({ ...state });
    }

    this.currentCycle = savedCycle;
    this.computeCurrentCycle();
    this._suppressNotify = false;
    return this.fullTrace;
  }

  // ── Initialize with defaults ────────────────────────────────────
  init() {
    this.computeCurrentCycle();
    this.runFullSimulation();
    this._notify();
  }
}
