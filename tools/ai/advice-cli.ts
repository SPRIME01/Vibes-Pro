#!/usr/bin/env tsx
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';

import { AIContextManager } from './src/context-manager.js';
import type { ContextSource } from './src/context-manager.js';
import { PerformanceMonitor } from '../performance/monitor.js';
import type { PerformanceAdvisory } from '../performance/monitor.js';

interface RecommendationPayload {
  generated: RecommendationDTO[];
  existing: RecommendationDTO[];
  retention_deleted: number;
  feedback?: {
    id: string;
    action: string;
  } | null;
}

interface RecommendationDTO {
  id: string;
  pattern_name: string;
  decision_point: string;
  confidence: number;
  provenance: string;
  rationale: string;
  created_at: string;
  expires_at: string;
  metadata: Record<string, unknown>;
}

interface CliOptions {
  dbPath: string;
  lookback: number;
  dryRun: boolean;
  task?: string;
  limit: number;
  retention: number;
  acceptId?: string;
  dismissId?: string;
  reason?: string;
  baselinePath?: string;
}

function parseArgs(argv: string[]): CliOptions {
  const options: CliOptions = {
    dbPath: resolve('tmp/ai-guidance'),
    lookback: 45,
    dryRun: false,
    limit: 10,
    retention: 90,
    baselinePath: resolve('tmp/performance-baselines.json')
  };

  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    switch (arg) {
      case '--db':
      case '--database':
        options.dbPath = resolve(argv[++index] ?? options.dbPath);
        break;
      case '--lookback':
        options.lookback = Number.parseInt(argv[++index] ?? `${options.lookback}`, 10);
        break;
      case '--limit':
        options.limit = Number.parseInt(argv[++index] ?? `${options.limit}`, 10);
        break;
      case '--retention':
        options.retention = Number.parseInt(argv[++index] ?? `${options.retention}`, 10);
        break;
      case '--dry-run':
        options.dryRun = true;
        break;
      case '--task':
        options.task = argv[++index];
        break;
      case '--accept':
        options.acceptId = argv[++index];
        break;
      case '--dismiss':
        options.dismissId = argv[++index];
        break;
      case '--reason':
        options.reason = argv[++index];
        break;
      case '--baseline': {
        const baselineArg = argv[++index];
        if (!baselineArg) {
          console.error('Error: --baseline requires a path argument.');
          process.exit(1);
        }
        options.baselinePath = resolve(baselineArg);
        break;
      }
      default:
        if (!arg.startsWith('--')) {
          options.task = arg;
        }
    }
  }

  return options;
}

function runPythonExporter(options: CliOptions): RecommendationPayload {
  const pythonModule = 'temporal_db.python.export_recommendations';
  const args = [
    '-m',
    pythonModule,
    '--db',
    options.dbPath,
    '--lookback',
    `${options.lookback}`,
    '--limit',
    `${options.limit}`,
    '--retention',
    `${options.retention}`
  ];

  if (options.dryRun) {
    args.push('--dry-run');
  }
  if (options.acceptId) {
    args.push('--feedback-action', 'accept', '--feedback-id', options.acceptId);
    if (options.reason) {
      args.push('--feedback-reason', options.reason);
    }
  }
  if (options.dismissId) {
    args.push('--feedback-action', 'dismiss', '--feedback-id', options.dismissId);
    if (options.reason) {
      args.push('--feedback-reason', options.reason);
    }
  }

  const env = {
    ...process.env,
    PYTHONPATH: process.env.PYTHONPATH
      ? `${process.env.PYTHONPATH}:${resolve('.')}`
      : resolve('.')
  };

  const result = spawnSync('python', args, {
    encoding: 'utf-8',
    stdio: ['ignore', 'pipe', 'pipe'],
    env
  });

  if (result.status !== 0) {
    throw new Error(result.stderr || 'Python exporter failed');
  }

  return JSON.parse(result.stdout) as RecommendationPayload;
}

function mergeRecommendations(payload: RecommendationPayload): RecommendationDTO[] {
  const map = new Map<string, RecommendationDTO>();
  [...payload.generated, ...payload.existing].forEach((recommendation) => {
    map.set(recommendation.id, recommendation);
  });
  return [...map.values()].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}

function createContextSources(recommendations: RecommendationDTO[], advisories: PerformanceAdvisory[]): ContextSource[] {
  const sources: ContextSource[] = recommendations.map((recommendation) => {
    const metadata = recommendation.metadata ?? {};
    const tagsValue = (metadata as { tags?: unknown }).tags;
    const tags = Array.isArray(tagsValue) ? tagsValue.map((tag) => String(tag)) : [];
    const successRateValue = (metadata as { success_rate?: unknown }).success_rate;
    const successRate = typeof successRateValue === 'number' ? successRateValue : undefined;

    return {
      id: `pattern:${recommendation.id.slice(0, 8)}`,
      priority: 0.8,
      tags,
      lastUpdated: new Date(recommendation.created_at),
      successRate,
      patternConfidence: recommendation.confidence,
      provenance: recommendation.provenance,
      performanceDelta: 0,
      async getContent() {
        const contextsValue = (metadata as { top_contexts?: unknown }).top_contexts;
        const contexts = Array.isArray(contextsValue) ? contextsValue.map((value) => String(value)) : [];
        const contextSection = contexts.length > 0 ? `Top contexts: ${contexts.join(', ')}` : '';
        return [recommendation.rationale, `Decision Point: ${recommendation.decision_point}`, contextSection]
          .filter(Boolean)
          .join('\n');
      }
    } satisfies ContextSource;
  });

  advisories.forEach((advisory, index) => {
    sources.push({
      id: `advisory:${advisory.workflow}:${index}`,
      priority: 0.6,
      tags: [advisory.workflow, 'telemetry'],
      lastUpdated: new Date(advisory.timestamp),
      successRate: 0.4,
      patternConfidence: 0.4,
      provenance: 'performance-monitor',
      performanceDelta: advisory.deltaPct,
      async getContent() {
        return [
          advisory.message,
          `Observed: ${advisory.observed.toFixed(2)}ms`,
          `Baseline: ${advisory.baseline.toFixed(2)}ms`,
          `Threshold: ${(advisory.thresholdPct * 100).toFixed(0)}%`
        ].join('\n');
      }
    });
  });

  return sources;
}

function printRecommendations(recommendations: RecommendationDTO[]): void {
  if (recommendations.length === 0) {
    console.log('No pattern recommendations available. Run with recent temporal snapshots to populate insights.');
    return;
  }

  recommendations.forEach((recommendation) => {
    const expiry = new Date(recommendation.expires_at).toISOString().split('T')[0];
    console.log(`- ${recommendation.pattern_name} (confidence ${(recommendation.confidence * 100).toFixed(1)}%)`);
    console.log(`  Decision Point: ${recommendation.decision_point} | Provenance: ${recommendation.provenance} | Expires: ${expiry}`);
    console.log(`  ${recommendation.rationale}`);
  });
}

function printAdvisories(advisories: PerformanceAdvisory[]): void {
  if (advisories.length === 0) {
    console.log('No active performance advisories. Baselines are healthy.');
    return;
  }

  advisories.forEach((advisory) => {
    console.log(`- [${advisory.severity.toUpperCase()}] ${advisory.message}`);
  });
}

async function main(): Promise<void> {
  const options = parseArgs(process.argv);

  try {
    const payload = runPythonExporter(options);
    const mergedRecommendations = mergeRecommendations(payload);

    console.log('=== AI Guidance Fabric ===');
    console.log('');
    if (options.acceptId) {
      console.log(`Recorded acceptance feedback for recommendation ${options.acceptId}.`);
    }
    if (options.dismissId) {
      console.log(`Recorded dismissal feedback for recommendation ${options.dismissId}.`);
    }
    if (payload.retention_deleted > 0) {
      console.log(`Purged ${payload.retention_deleted} expired recommendations during refresh.`);
    }

    console.log('');
    console.log('Pattern Recommendations');
    console.log('-----------------------');
    printRecommendations(mergedRecommendations);

    const monitor = new PerformanceMonitor({ baselinePath: options.baselinePath, persist: false });
    const advisories = monitor.getAdvisories();

    console.log('');
    console.log('Performance Advisories');
    console.log('----------------------');
    printAdvisories(advisories);

    if (options.task) {
      const manager = new AIContextManager({
        maxTokens: 1600,
        reservedTokens: 200,
        weights: {
          performance: 0.15,
          patternConfidence: 0.2,
          relevance: 0.35,
          recency: 0.15,
          success: 0.1,
          priority: 0.05
        }
      });

      const sources = createContextSources(mergedRecommendations, advisories);
      manager.registerSources(sources);

      const context = await manager.getOptimalContext(options.task);

      console.log('');
      console.log(`Context Bundle for Task: ${options.task}`);
      console.log('------------------------------');
      console.log(context.content);
      console.log('');
      console.log('Selected Sources:');
      context.sources.forEach((source) => {
        const fields = [
          `score=${source.score.toFixed(2)}`,
          source.confidence !== undefined ? `confidence=${(source.confidence * 100).toFixed(1)}%` : undefined,
          source.provenance ? `provenance=${source.provenance}` : undefined,
          source.performanceDelta ? `perfDelta=${(source.performanceDelta * 100).toFixed(1)}%` : undefined
        ].filter(Boolean);
        console.log(`- ${source.id} (${fields.join(', ')})`);
      });
    } else {
      console.log('');
      console.log('Tip: Provide a task description (e.g., `--task "Implement API gateway"`) to generate a context bundle.');
    }

    console.log('');
    console.log('Use --accept <id> or --dismiss <id> to record feedback and tune future guidance.');
  } catch (error) {
    console.error('Failed to produce AI guidance:', error);
    process.exitCode = 1;
  }
}

void main();
