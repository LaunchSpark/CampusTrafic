import { get } from './client';

export function getMetrics(runId) {
  return get(`/runs/${runId}/metrics`);
}
