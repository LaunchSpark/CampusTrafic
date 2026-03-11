import { get } from './client';

export function getWorld(runId) {
  return get(`/runs/${runId}/world`);
}
