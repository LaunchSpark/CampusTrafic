import { useState } from 'react';
import { getTrainingStatus, startTraining } from '../api/train';
import { useDateRange } from '../state/DateRangeContext';

function TrainPage() {
  const { startDate, endDate } = useDateRange();
  const [statusResponse, setStatusResponse] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const runAction = async (action) => {
    setIsLoading(true);
    setErrorMessage('');

    try {
      const response = await action();
      setStatusResponse(response);
    } catch (error) {
      if (error.status === 404) {
        setErrorMessage('Training endpoints not implemented yet.');
      } else {
        setErrorMessage('Unable to reach training service. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="row g-4">
      <div className="col-12">
        <h1 className="h3">Training Observability</h1>
        <p className="text-muted mb-0">
          Date range context: <strong>{startDate}</strong> to <strong>{endDate}</strong>
        </p>
      </div>

      <div className="col-12">
        <div className="card shadow-sm">
          <div className="card-body">
            <h2 className="h5">Live training graphs placeholder</h2>
            {/* TODO: Add chart components and stream subscriptions in a later milestone. */}
            <p className="text-muted mb-0">Charts and streaming metrics will be integrated in a follow-up.</p>
          </div>
        </div>
      </div>

      <div className="col-12">
        <div className="card shadow-sm">
          <div className="card-body d-flex flex-wrap gap-2 align-items-center">
            <button
              type="button"
              className="btn btn-outline-primary"
              onClick={() => runAction(getTrainingStatus)}
              disabled={isLoading}
            >
              Check status
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => runAction(startTraining)}
              disabled={isLoading}
            >
              Start training
            </button>
          </div>
          {errorMessage && <div className="alert alert-warning m-3 mb-0">{errorMessage}</div>}
          {statusResponse && (
            <pre className="bg-light border rounded m-3 p-3 mb-0">
              {JSON.stringify(statusResponse, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

export default TrainPage;
