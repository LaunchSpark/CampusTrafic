import { get } from './client';

export function getFieldIndex(runId) {
  return get(`/runs/${runId}/fields/index`);
}

export function getTile(runId, tileId) {
  return get(`/runs/${runId}/fields/tiles/${tileId}`);
}
