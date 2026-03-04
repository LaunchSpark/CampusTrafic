import { get, post } from './client';

export function startTraining() {
  return post('/train/start');
}

export function getTrainingStatus() {
  return get('/train/status');
}

export function getTrainingLogs() {
  return get('/train/logs');
}

export function getLiveMetrics() {
  return get('/train/metrics/live');
}
