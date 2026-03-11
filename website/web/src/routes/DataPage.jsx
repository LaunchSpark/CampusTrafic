import { useEffect, useState } from 'react';
import { getFieldIndex } from '../api/fields';
import { getMetrics } from '../api/metrics';
import { listRuns } from '../api/runs';
import { getWorld } from '../api/world';
import { useDateRange } from '../state/DateRangeContext';

function DataPage() {
  const { startDate, endDate } = useDateRange();
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [status, setStatus] = useState({ world: false, fields: false, metrics: false });

  useEffect(() => {
    const loadRuns = async () => {
      setLoadingRuns(true);
      setLoadError('');
      try {
        const data = await listRuns();
        const normalizedRuns = Array.isArray(data) ? data : data?.runs || [];
        setRuns(normalizedRuns);

        if (normalizedRuns.length > 0) {
          const firstRun = normalizedRuns[0];
          const runId = typeof firstRun === 'object' ? firstRun.run_id || firstRun.id : firstRun;
          if (runId) {
            setSelectedRunId(String(runId));
          }
        }
      } catch (error) {
        setLoadError(`Unable to load runs: ${error.message}`);
      } finally {
        setLoadingRuns(false);
      }
    };

    loadRuns();
  }, []);

  const handleLoad = async () => {
    if (!selectedRunId) {
      setLoadError('Select a run to continue.');
      return;
    }

    setLoadingData(true);
    setLoadError('');

    try {
      const [worldResult, fieldResult, metricsResult] = await Promise.allSettled([
        getWorld(selectedRunId),
        getFieldIndex(selectedRunId),
        getMetrics(selectedRunId),
      ]);

      setStatus({
        world: worldResult.status === 'fulfilled',
        fields: fieldResult.status === 'fulfilled',
        metrics: metricsResult.status === 'fulfilled',
      });

      const failed = [worldResult, fieldResult, metricsResult].filter((result) => result.status === 'rejected');
      if (failed.length > 0) {
        setLoadError('Some resources failed to load. Check backend availability and run artifacts.');
      }
    } finally {
      setLoadingData(false);
    }
  };

  return (
    <div className="row g-4">
      <div className="col-12">
        <h1 className="h3">Data</h1>
        <p className="text-muted mb-0">
          Selected date range: <strong>{startDate}</strong> to <strong>{endDate}</strong>
        </p>
      </div>

      <div className="col-12">
        <div className="card shadow-sm">
          <div className="card-body">
            <div className="row g-3 align-items-end">
              <div className="col-md-8">
                <label className="form-label" htmlFor="runSelect">
                  Run ID
                </label>
                <select
                  id="runSelect"
                  className="form-select"
                  value={selectedRunId}
                  onChange={(event) => setSelectedRunId(event.target.value)}
                  disabled={loadingRuns}
                >
                  <option value="">Select a run</option>
                  {runs.map((run) => {
                    const runId = typeof run === 'object' ? run.run_id || run.id : run;
                    return (
                      <option key={String(runId)} value={String(runId)}>
                        {String(runId)}
                      </option>
                    );
                  })}
                </select>
              </div>
              <div className="col-md-4 d-grid">
                <button type="button" className="btn btn-primary" onClick={handleLoad} disabled={loadingData}>
                  {loadingData ? 'Loading...' : 'Load'}
                </button>
              </div>
            </div>
            {loadError && <div className="alert alert-warning mt-3 mb-0">{loadError}</div>}
          </div>
        </div>
      </div>

      <div className="col-lg-4">
        <div className="card shadow-sm h-100">
          <div className="card-body">
            <h2 className="h6">World</h2>
            <p className={status.world ? 'text-success mb-0' : 'text-muted mb-0'}>
              Loaded: {status.world ? 'Yes' : 'No'}
            </p>
          </div>
        </div>
      </div>

      <div className="col-lg-4">
        <div className="card shadow-sm h-100">
          <div className="card-body">
            <h2 className="h6">Fields Index</h2>
            <p className={status.fields ? 'text-success mb-0' : 'text-muted mb-0'}>
              Loaded: {status.fields ? 'Yes' : 'No'}
            </p>
          </div>
        </div>
      </div>

      <div className="col-lg-4">
        <div className="card shadow-sm h-100">
          <div className="card-body">
            <h2 className="h6">Metrics</h2>
            <p className={status.metrics ? 'text-success mb-0' : 'text-muted mb-0'}>
              Loaded: {status.metrics ? 'Yes' : 'No'}
            </p>
          </div>
        </div>
      </div>

      <div className="col-12">
        <div className="card border-secondary-subtle">
          <div className="card-body">
            {/* TODO: Replace this placeholder with vector field rendering in a follow-up iteration. */}
            <h2 className="h5">Vector field visualization placeholder</h2>
            <p className="text-muted mb-0">Visualization components will be added here once APIs are finalized.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DataPage;
