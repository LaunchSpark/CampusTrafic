import { get } from './client';

export function listRuns() {
  return get('/runs');
}
