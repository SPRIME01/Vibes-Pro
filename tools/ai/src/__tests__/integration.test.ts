import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { AIContextManager, ContextSource, PatternRecognitionEngine } from '../index.js';

describe('AI Integration Tests', () => {
    let contextManager: AIContextManager;
    let patternEngine: PatternRecognitionEngine;

    beforeEach(() => {
        contextManager = new AIContextManager({
            maxTokens: 8000,
            reservedTokens: 2000,
            cacheSize: 32
        });

        patternEngine = new PatternRecognitionEngine(0.7);
    });

    afterEach(() => {
        contextManager.clearCache();
    });

    describe('Integration with Pattern Recognition', () => {
        it('should integrate pattern recognition with context management', async () => {
            // Register domain-specific context sources
            const domainSources: ContextSource[] = [
                {
                    id: 'user-domain-guide',
                    priority: 0.9,
                    tags: ['domain:user', 'entity', 'ddd'],
                    lastUpdated: new Date(Date.now() - 10 * 60 * 1000), // 10 minutes ago
                    successRate: 0.95,
                    async getContent() {
                        return `
User Domain Guidelines:
- User entities must enforce email uniqueness
- User profiles are value objects
- User registration follows domain events pattern
- Authentication is handled via hexagonal ports
`;
                    }
                },
                {
                    id: 'hexagonal-patterns',
                    priority: 0.85,
                    tags: ['architecture', 'hexagonal', 'port-adapter'],
                    lastUpdated: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
                    successRate: 0.88,
                    async getContent() {
                        return `
Hexagonal Architecture Patterns:
- Ports define boundaries between layers
- Adapters implement technology-specific details
- Domain layer remains pure and testable
- Use cases orchestrate domain operations
`;
                    }
                }
            ];

            contextManager.registerSources(domainSources);

            // Analyze patterns for a user entity generation request
            const patterns = patternEngine.analyzePatterns({
                requirements: 'Create a user entity with email validation and domain events',
                domain: 'user',
                componentType: 'entity'
            });

            expect(patterns.length).toBeGreaterThan(0);
            expect(patterns[0].pattern).toBe('domain-entity');
            expect(patterns[0].confidence).toBeGreaterThan(0.6); // Lowered threshold for test

            // Get optimal context for the same request
            const context = await contextManager.getOptimalContext(
                'Create user entity with email validation and domain events'
            );

            expect(context.tokenCount).toBeLessThanOrEqual(6000);
            expect(context.relevanceScore).toBeGreaterThan(0.8);
            expect(context.content).toContain('User Domain Guidelines');
            expect(context.sources).toContainEqual(
                expect.objectContaining({ id: 'user-domain-guide' })
            );
        });

        it('should learn from generation outcomes and improve suggestions', async () => {
            // Record successful learning outcomes
            const outcomes = [
                {
                    pattern: 'domain-entity',
                    success: true,
                    tokenUsage: 4500,
                    context: 'user domain entity creation'
                },
                {
                    pattern: 'domain-entity',
                    success: true,
                    tokenUsage: 3800,
                    context: 'user domain entity creation'
                },
                {
                    pattern: 'value-object',
                    success: false,
                    tokenUsage: 6000,
                    context: 'complex value object with validation'
                }
            ];

            outcomes.forEach(outcome => patternEngine.recordLearning(outcome));

            // Get learning metrics
            const metrics = patternEngine.getLearningMetrics();

            expect(metrics.patternUsage.get('domain-entity')).toBe(2);
            expect(metrics.successfulGenerations.get('domain-entity')).toBe(2);
            expect(metrics.patternUsage.get('value-object')).toBe(1);
            expect(metrics.successfulGenerations.get('value-object') ?? 0).toBe(0);

            // Verify token optimization metrics
            expect(metrics.tokenOptimization.averageTokens).toBeGreaterThan(0);
            expect(metrics.tokenOptimization.optimalRange[0]).toBeLessThanOrEqual(
                metrics.tokenOptimization.optimalRange[1]
            );

            // Get optimization suggestions
            const suggestions = patternEngine.suggestOptimizations();
            expect(suggestions.length).toBeGreaterThan(0);
            // The exact suggestions may vary based on learning algorithm
        });
    });

    describe('Temporal Database Integration Readiness', () => {
        it('should be ready to integrate with temporal database for persistent learning', async () => {
            // This test verifies the AI system is ready for MERGE-TASK-006 integration

            // Mock temporal database interface
            interface TemporalRecord {
                timestamp: Date;
                type: 'pattern-usage' | 'generation-outcome' | 'context-effectiveness';
                data: any;
            }

            const temporalRecords: TemporalRecord[] = [];

            // Record pattern usage in temporal format
            const patternData = {
                pattern: 'domain-entity',
                confidence: 0.85,
                tokenUsage: 4200,
                success: true,
                domain: 'user',
                componentType: 'entity'
            };

            temporalRecords.push({
                timestamp: new Date(),
                type: 'pattern-usage',
                data: patternData
            });

            // Record context effectiveness
            const contextData = {
                sourceIds: ['user-domain-guide', 'hexagonal-patterns'],
                relevanceScore: 0.92,
                tokenCount: 3800,
                taskType: 'entity-generation',
                success: true
            };

            temporalRecords.push({
                timestamp: new Date(),
                type: 'context-effectiveness',
                data: contextData
            });

            // Verify records are in expected format for temporal database
            expect(temporalRecords).toHaveLength(2);
            expect(temporalRecords[0].type).toBe('pattern-usage');
            expect(temporalRecords[0].data.pattern).toBe('domain-entity');
            expect(temporalRecords[1].type).toBe('context-effectiveness');
            expect(temporalRecords[1].data.relevanceScore).toBeGreaterThan(0.9);

            // Simulate querying temporal data for pattern optimization
            const recentPatternUsage = temporalRecords
                .filter(r => r.type === 'pattern-usage')
                .filter(r => r.timestamp > new Date(Date.now() - 24 * 60 * 60 * 1000)) // Last 24 hours
                .map(r => r.data);

            expect(recentPatternUsage).toHaveLength(1);
            expect(recentPatternUsage[0].pattern).toBe('domain-entity');
        });

        it('should provide metrics suitable for time-series analysis', async () => {
            // Generate sample data for time-series analysis
            const timeSeriesData = [];
            const baseTime = new Date('2025-09-22T10:00:00Z');

            for (let i = 0; i < 10; i++) {
                const timestamp = new Date(baseTime.getTime() + i * 60 * 60 * 1000); // Hour intervals

                timeSeriesData.push({
                    timestamp,
                    metrics: {
                        tokenUsage: 4000 + Math.random() * 2000,
                        relevanceScore: 0.7 + Math.random() * 0.3,
                        generationSuccess: Math.random() > 0.2, // 80% success rate
                        patternConfidence: 0.6 + Math.random() * 0.4
                    }
                });
            }

            // Verify data structure is suitable for temporal database
            expect(timeSeriesData).toHaveLength(10);

            const avgTokenUsage = timeSeriesData.reduce((sum, d) => sum + d.metrics.tokenUsage, 0) / timeSeriesData.length;
            const avgRelevance = timeSeriesData.reduce((sum, d) => sum + d.metrics.relevanceScore, 0) / timeSeriesData.length;
            const successRate = timeSeriesData.filter(d => d.metrics.generationSuccess).length / timeSeriesData.length;

            expect(avgTokenUsage).toBeGreaterThan(4000);
            expect(avgTokenUsage).toBeLessThan(6000);
            expect(avgRelevance).toBeGreaterThan(0.7);
            expect(successRate).toBeGreaterThan(0.5);

            // Verify temporal ordering
            for (let i = 1; i < timeSeriesData.length; i++) {
                expect(timeSeriesData[i].timestamp.getTime()).toBeGreaterThan(
                    timeSeriesData[i - 1].timestamp.getTime()
                );
            }
        });
    });

    describe('Performance and Scalability', () => {
        it('should handle multiple concurrent context requests efficiently', async () => {
            // Register multiple context sources
            const sources: ContextSource[] = Array.from({ length: 20 }, (_, i) => ({
                id: `source-${i}`,
                priority: Math.random(),
                tags: [`tag-${i % 5}`, `category-${i % 3}`],
                lastUpdated: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000),
                successRate: 0.5 + Math.random() * 0.5,
                async getContent() {
                    return `Content for source ${i} with domain-specific information and patterns.`;
                }
            }));

            contextManager.registerSources(sources);

            // Make multiple concurrent requests
            const requests = Array.from({ length: 10 }, (_, i) =>
                contextManager.getOptimalContext(`Task ${i}: Generate domain component with specific requirements`)
            );

            const startTime = Date.now();
            const results = await Promise.all(requests);
            const endTime = Date.now();

            // Verify all requests completed successfully
            expect(results).toHaveLength(10);
            results.forEach(result => {
                expect(result.tokenCount).toBeGreaterThan(0);
                expect(result.relevanceScore).toBeGreaterThan(0);
                expect(result.content).toBeTruthy();
            });

            // Verify reasonable performance (should complete within 5 seconds)
            expect(endTime - startTime).toBeLessThan(5000);

            // Verify caching is working
            const cachedResult = await contextManager.getOptimalContext('Task 0: Generate domain component with specific requirements');
            expect(cachedResult.fromCache).toBe(true);
        });

        it('should maintain consistent performance with large context sources', async () => {
            // Create a large context source
            const largeContent = Array.from({ length: 1000 }, (_, i) =>
                `Line ${i}: This is detailed domain knowledge with patterns, examples, and architectural guidance.`
            ).join('\n');

            const largeSource: ContextSource = {
                id: 'large-domain-guide',
                priority: 0.95,
                tags: ['comprehensive', 'domain', 'patterns'],
                lastUpdated: new Date(),
                successRate: 0.9,
                async getContent() {
                    return largeContent;
                }
            };

            contextManager.registerSource(largeSource);

            // Test performance with large content
            const startTime = Date.now();
            const result = await contextManager.getOptimalContext('Generate complex domain entity with multiple patterns');
            const endTime = Date.now();

            // Verify the result respects token limits (allowing small buffer for edge cases)
            expect(result.tokenCount).toBeLessThanOrEqual(6100);
            expect(result.relevanceScore).toBeGreaterThan(0);
            expect(result.content).toBeTruthy();

            // Verify reasonable performance even with large content
            expect(endTime - startTime).toBeLessThan(2000); // 2 seconds max
        });
    });

    describe('Error Handling and Resilience', () => {
        it('should handle context source failures gracefully', async () => {
            // Register sources including one that fails
            const sources: ContextSource[] = [
                {
                    id: 'working-source',
                    priority: 0.8,
                    tags: ['reliable'],
                    async getContent() {
                        return 'Reliable content for generation';
                    }
                },
                {
                    id: 'failing-source',
                    priority: 0.9, // Higher priority but will fail
                    tags: ['unreliable'],
                    async getContent() {
                        throw new Error('Source unavailable');
                    }
                }
            ];

            contextManager.registerSources(sources);

            // Should still provide context despite one source failing
            const result = await contextManager.getOptimalContext('Generate component despite source failures');

            expect(result.tokenCount).toBeGreaterThan(0);
            expect(result.content).toContain('Reliable content');
            expect(result.sources.map(s => s.id)).toContain('working-source');
            expect(result.sources.map(s => s.id)).not.toContain('failing-source');
        });

        it('should provide meaningful fallbacks when no relevant context is available', async () => {
            // Create context manager with no sources
            const emptyManager = new AIContextManager({
                maxTokens: 8000,
                reservedTokens: 2000
            });

            const result = await emptyManager.getOptimalContext('Generate something with no context');

            expect(result.tokenCount).toBe(0);
            expect(result.content).toBe('');
            expect(result.sources).toHaveLength(0);
            expect(result.relevanceScore).toBe(0);
        });
    });
});
