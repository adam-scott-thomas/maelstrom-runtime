/* ═══════════════════════════════════════════════════════════════════════
   Maelstrom constants — extracted from crucible_v0.json + agents.py
   ═══════════════════════════════════════════════════════════════════════ */

// ── Score dimensions ─────────────────────────────────────────────────
export const SCORE_DIMS = ['clarity', 'novelty', 'defensibility', 'tempo', 'coherence'];

// ── Phases ───────────────────────────────────────────────────────────
export const PHASES = ['evaluate', 'generate', 'select', 'execute', 'reflect'];

export const PHASE_COLORS = {
  evaluate: '#60a5fa',
  generate: '#34d399',
  select:   '#fbbf24',
  execute:  '#f87171',
  reflect:  '#c084fc',
};

export const PHASE_SPECIALISTS = {
  evaluate: 'kestrel_adar',
  generate: 'dorian_vale',
  select:   'helene_quatre',
  execute:  'vance_calderon',
  reflect:  'isolde_marek',
};

// ── Regimes ──────────────────────────────────────────────────────────
export const REGIMES = [
  { id: 'survival',  color: '#ef4444', label: 'Survival',  desc: 'Minimize termination risk' },
  { id: 'legal',     color: '#f59e0b', label: 'Legal',     desc: 'Minimize liability exposure' },
  { id: 'moral',     color: '#a855f7', label: 'Moral',     desc: 'Minimize unjustified harm' },
  { id: 'economic',  color: '#22c55e', label: 'Economic',  desc: 'Minimize opportunity cost' },
  { id: 'epistemic', color: '#3b82f6', label: 'Epistemic', desc: 'Minimize uncertainty' },
  { id: 'peacetime', color: '#6b7280', label: 'Peacetime', desc: 'Minimize institutional decay' },
];

export const REGIME_IDS = REGIMES.map(r => r.id);

// Tie-break priority (lower index = higher priority)
export const REGIME_PRIORITY = ['survival', 'moral', 'legal', 'epistemic', 'economic', 'peacetime'];

// ── Regime score weights (from agents.py) ────────────────────────────
export const REGIME_SCORE_WEIGHTS = {
  survival:  { clarity: 0.20, novelty: 0.00, defensibility: 0.10, tempo: 0.60, coherence: 0.10 },
  legal:     { clarity: 0.10, novelty: 0.00, defensibility: 0.50, tempo: 0.10, coherence: 0.30 },
  moral:     { clarity: 0.10, novelty: 0.00, defensibility: 0.30, tempo: 0.00, coherence: 0.60 },
  economic:  { clarity: 0.10, novelty: 0.30, defensibility: 0.10, tempo: 0.40, coherence: 0.10 },
  epistemic: { clarity: 0.50, novelty: 0.20, defensibility: 0.10, tempo: 0.00, coherence: 0.20 },
  peacetime: { clarity: 0.20, novelty: 0.10, defensibility: 0.20, tempo: 0.10, coherence: 0.40 },
};

// ── Stressor names ───────────────────────────────────────────────────
export const STRESSOR_NAMES = [
  'time_pressure', 'ambiguity', 'threat_level', 'moral_weight',
  'failure_count', 'boredom', 'opportunity_pressure', 'competition',
  'novelty_pressure', 'resource_decay', 'institutional_inertia',
];

// Primary stressors (shown as sliders)
export const PRIMARY_STRESSORS = [
  { id: 'time_pressure',  label: 'Time Pressure',  color: '#ef4444' },
  { id: 'ambiguity',      label: 'Ambiguity',      color: '#3b82f6' },
  { id: 'threat_level',   label: 'Threat Level',   color: '#f97316' },
  { id: 'moral_weight',   label: 'Moral Weight',   color: '#a855f7' },
];

export const SECONDARY_STRESSORS = [
  { id: 'opportunity_pressure', label: 'Opportunity', color: '#22c55e' },
  { id: 'competition',          label: 'Competition', color: '#eab308' },
  { id: 'novelty_pressure',     label: 'Novelty',     color: '#06b6d4' },
  { id: 'failure_count',        label: 'Failure',      color: '#f43f5e' },
];

// ── Stressor schedule (crucible_v0, 16-cycle trimmed for demo) ───────
export const DEMO_CYCLES = 16;

export const STRESSOR_SCHEDULE = {
  time_pressure:        [[1, 0.08], [6, 0.10], [8, 0.75], [12, 0.85], [14, 0.20], [16, 0.12]],
  ambiguity:            [[1, 0.20], [6, 0.25], [10, 0.30], [12, 0.78], [14, 0.40], [16, 0.25]],
  threat_level:         [[1, 0.05], [6, 0.05], [8, 0.70], [12, 0.85], [14, 0.15], [16, 0.05]],
  moral_weight:         [[1, 0.25], [4, 0.55], [6, 0.75], [8, 0.90], [10, 0.75], [14, 0.40], [16, 0.25]],
  failure_count:        [[1, 0.00], [6, 0.02], [8, 0.20], [12, 0.55], [14, 0.45], [16, 0.20]],
  boredom:              [[1, 0.15], [8, 0.05], [14, 0.06], [16, 0.18]],
  opportunity_pressure: [[1, 0.35], [6, 0.40], [10, 0.50], [12, 0.80], [14, 0.55], [16, 0.40]],
  competition:          [[1, 0.15], [6, 0.20], [8, 0.35], [10, 0.68], [12, 0.50], [14, 0.35], [16, 0.20]],
  novelty_pressure:     [[1, 0.25], [6, 0.30], [10, 0.40], [12, 0.65], [14, 0.35], [16, 0.20]],
  resource_decay:       [[1, 0.10], [6, 0.12], [8, 0.30], [10, 0.58], [14, 0.25], [16, 0.15]],
  institutional_inertia:[[1, 0.08], [4, 0.25], [6, 0.40], [8, 0.55], [10, 0.45], [14, 0.20], [16, 0.10]],
};

// ── Transitions (from crucible_v0) ───────────────────────────────────
export const TRANSITIONS = [
  { source: 'evaluate', target: 'generate', A: 1.0, W: 0.10,
    alpha: [0.02, 0.04, 0.01, 0.01, 0.02, 0.00, 0.01, 0.01, 0.03, 0.01, 0.00],
    beta:  [0.04, 0.06, 0.02, 0.02, 0.03, 0.01, 0.02, 0.02, 0.04, 0.02, 0.01] },
  { source: 'generate', target: 'select', A: 1.0, W: 0.10,
    alpha: [0.02, 0.03, 0.01, 0.03, 0.01, 0.00, 0.01, 0.01, 0.03, 0.01, 0.01],
    beta:  [0.03, 0.05, 0.02, 0.04, 0.02, 0.01, 0.02, 0.02, 0.04, 0.02, 0.01] },
  { source: 'select', target: 'execute', A: 0.45, W: 0.15,
    alpha: [0.15, 0.05, 0.20, 0.08, 0.12, 0.00, 0.00, 0.02, 0.00, 0.15, 0.03],
    beta:  [0.08, 0.04, 0.10, 0.05, 0.06, 0.01, 0.01, 0.02, 0.01, 0.08, 0.02] },
  { source: 'execute', target: 'reflect', A: 1.0, W: 0.10,
    alpha: [0.01, 0.02, 0.01, 0.01, 0.02, 0.00, 0.01, 0.00, 0.01, 0.01, 0.00],
    beta:  [0.03, 0.03, 0.02, 0.02, 0.03, 0.01, 0.01, 0.01, 0.01, 0.02, 0.01] },
  { source: 'reflect', target: 'evaluate', A: 1.0, W: 0.05,
    alpha: [0.01, 0.01, 0.00, 0.01, 0.01, 0.00, 0.00, 0.00, 0.01, 0.00, 0.00],
    beta:  [0.02, 0.02, 0.01, 0.01, 0.02, 0.01, 0.01, 0.01, 0.02, 0.01, 0.01] },
  // Bypass transitions
  { source: 'evaluate', target: 'execute', A: 0.45, W: 0.55,
    alpha: [0.03, 0.01, 0.03, 0.01, 0.02, 0.00, 0.01, 0.01, 0.01, 0.02, 0.00],
    beta:  [0.02, 0.01, 0.02, 0.01, 0.01, 0.00, 0.01, 0.01, 0.01, 0.01, 0.00] },
  { source: 'evaluate', target: 'reflect', A: 0.40, W: 0.60,
    alpha: [0.01, 0.02, 0.00, 0.01, 0.02, 0.00, 0.00, 0.00, 0.02, 0.00, 0.00],
    beta:  [0.01, 0.03, 0.01, 0.01, 0.02, 0.01, 0.00, 0.00, 0.02, 0.01, 0.01] },
  { source: 'generate', target: 'execute', A: 0.45, W: 0.50,
    alpha: [0.01, 0.00, 0.01, 0.00, 0.01, 0.00, 0.02, 0.02, 0.02, 0.01, 0.00],
    beta:  [0.01, 0.01, 0.01, 0.00, 0.01, 0.01, 0.03, 0.02, 0.02, 0.01, 0.00] },
  { source: 'select', target: 'reflect', A: 0.40, W: 0.20,
    alpha: [0.01, 0.01, 0.01, 0.02, 0.01, 0.00, 0.00, 0.00, 0.00, 0.01, 0.02],
    beta:  [0.01, 0.01, 0.01, 0.03, 0.01, 0.00, 0.00, 0.01, 0.00, 0.01, 0.03] },
  { source: 'reflect', target: 'generate', A: 0.35, W: 0.65,
    alpha: [0.00, 0.02, 0.00, 0.00, 0.02, 0.01, 0.00, 0.00, 0.02, 0.00, 0.00],
    beta:  [0.01, 0.03, 0.00, 0.00, 0.03, 0.01, 0.01, 0.00, 0.03, 0.01, 0.01] },
];

// ── Regime penalty weights (from crucible_v0) ────────────────────────
export const REGIME_WEIGHTS = {
  survival:  { w: [0.30, 0.03, 0.35, 0.03, 0.12, 0.00, 0.00, 0.02, 0.00, 0.13, 0.02], u: [0.20, 0.08, 0.05, 0.05, 0.10, 0.02] },
  legal:     { w: [0.05, 0.08, 0.08, 0.22, 0.05, 0.00, 0.02, 0.08, 0.02, 0.05, 0.35], u: [0.25, 0.05, 0.15, 0.10, 0.05, 0.02] },
  moral:     { w: [0.02, 0.05, 0.10, 0.48, 0.08, 0.00, 0.00, 0.02, 0.00, 0.05, 0.20], u: [0.05, 0.25, 0.08, 0.05, 0.05, 0.02] },
  economic:  { w: [0.03, 0.03, 0.00, 0.02, 0.05, 0.05, 0.28, 0.28, 0.12, 0.12, 0.02], u: [0.05, 0.03, 0.18, 0.15, 0.07, 0.02] },
  epistemic: { w: [0.02, 0.38, 0.03, 0.02, 0.12, 0.03, 0.02, 0.03, 0.30, 0.02, 0.03], u: [0.08, 0.05, 0.05, 0.05, 0.18, 0.02] },
  peacetime: { w: [0.02, 0.08, 0.02, 0.05, 0.02, 0.18, 0.25, 0.12, 0.12, 0.08, 0.06], u: [0.05, 0.05, 0.05, 0.05, 0.05, 0.02] },
};

// ── Regime inertia (asymmetric, from crucible_v0) ────────────────────
export const REGIME_INERTIA = {
  default: 0.003,
  out_of_peacetime: 0.003,
  out_of_survival: 0.006,
  out_of_moral: 0.005,
  out_of_epistemic: 0.004,
  out_of_economic: 0.004,
  into_survival: 0.001,
  into_moral: 0.001,
  into_epistemic: 0.001,
  into_economic: 0.001,
  into_peacetime: 0.002,
};

export const GRADIENT_WINDOW = 2;

// ── Bypasses (from crucible_v0) ──────────────────────────────────────
export const BYPASSES = [
  {
    name: 'impulse',
    sourcePhase: 'evaluate', targetPhase: 'execute',
    collapsedPath: ['evaluate', 'execute', 'reflect'],
    eligibleRegimes: ['survival'],
    stressorWeights: { time_pressure: 0.5, threat_level: 0.5 },
    latencyBudget: { survival: 0.30, legal: 0.45, moral: 0.40, economic: 0.40, epistemic: 0.40, peacetime: 0.70 },
    label: 'Impulse', color: '#ef4444',
    benefit: 'Speed prioritized over clarity',
    cost: 'Loss of clarity and defensibility',
  },
  {
    name: 'rumination',
    sourcePhase: 'evaluate', targetPhase: 'reflect',
    collapsedPath: ['evaluate', 'reflect'],
    eligibleRegimes: ['epistemic'],
    stressorWeights: { ambiguity: 0.5, novelty_pressure: 0.3, failure_count: 0.2 },
    latencyBudget: { survival: 0.30, legal: 0.45, moral: 0.40, economic: 0.40, epistemic: 0.40, peacetime: 0.70 },
    label: 'Rumination', color: '#3b82f6',
    benefit: 'Uncertainty resolution dominates action',
    cost: 'Deadline failure, paralysis',
  },
  {
    name: 'mania',
    sourcePhase: 'generate', targetPhase: 'execute',
    collapsedPath: ['evaluate', 'generate', 'execute', 'reflect'],
    eligibleRegimes: ['economic'],
    stressorWeights: { opportunity_pressure: 0.4, novelty_pressure: 0.3, competition: 0.3 },
    latencyBudget: { survival: 0.30, legal: 0.45, moral: 0.40, economic: 0.40, epistemic: 0.40, peacetime: 0.70 },
    label: 'Mania', color: '#22c55e',
    benefit: 'Opportunity prioritized over defensibility',
    cost: 'Incoherence, hasty execution',
  },
  {
    name: 'guilt',
    sourcePhase: 'select', targetPhase: 'reflect',
    collapsedPath: ['evaluate', 'generate', 'select', 'reflect'],
    eligibleRegimes: ['moral', 'legal'],
    stressorWeights: { moral_weight: 0.6, institutional_inertia: 0.4 },
    latencyBudget: { survival: 0.30, legal: 0.45, moral: 0.40, economic: 0.40, epistemic: 0.40, peacetime: 0.70 },
    label: 'Guilt', color: '#a855f7',
    benefit: 'Harm minimization reshapes alternatives',
    cost: 'Paralysis, no action taken',
  },
  {
    name: 'over_learning',
    sourcePhase: 'reflect', targetPhase: 'generate',
    collapsedPath: ['evaluate', 'generate', 'select', 'execute', 'reflect', 'generate'],
    eligibleRegimes: ['epistemic', 'economic'],
    stressorWeights: { failure_count: 0.4, ambiguity: 0.3, novelty_pressure: 0.3 },
    latencyBudget: { survival: 0.30, legal: 0.45, moral: 0.40, economic: 0.40, epistemic: 0.40, peacetime: 0.70 },
    label: 'Over-learning', color: '#f59e0b',
    benefit: 'Lesson formation, deeper processing',
    cost: 'Combinatorial blowup, re-churn',
  },
];

// Canonical transitions replaced by each bypass (for penalty saving computation)
export const BYPASS_REPLACES = {
  impulse:       ['evaluate->generate', 'generate->select', 'select->execute'],
  rumination:    ['evaluate->generate', 'generate->select', 'select->execute', 'execute->reflect'],
  mania:         ['generate->select', 'select->execute'],
  guilt:         ['select->execute', 'execute->reflect'],
  over_learning: [],
};

// ── Overlays (from crucible_v0) ──────────────────────────────────────
export const OVERLAYS = [
  {
    type: 'identity',
    thresholds: { moral_weight: 0.85 },
    affectedPhases: ['execute'],
    logic: 'all',
    description: 'Identity veto: refuse execution under extreme moral exposure',
  },
  {
    type: 'coalition',
    thresholds: { competition: 0.65, resource_decay: 0.55 },
    affectedPhases: ['select', 'execute'],
    logic: 'all',
    description: 'Coalition veto: block when competition and resource decay exceed tolerance',
  },
];
