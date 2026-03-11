import { useDateRange } from '../state/DateRangeContext';

function DateRangePicker() {
  const { startDate, endDate, setStartDate, setEndDate } = useDateRange();

  return (
    <div className="d-flex align-items-center gap-2">
      <label className="text-white-50 small mb-0" htmlFor="startDate">
        Start
      </label>
      <input
        id="startDate"
        type="date"
        className="form-control form-control-sm"
        value={startDate}
        onChange={(event) => setStartDate(event.target.value)}
      />
      <label className="text-white-50 small mb-0" htmlFor="endDate">
        End
      </label>
      <input
        id="endDate"
        type="date"
        className="form-control form-control-sm"
        value={endDate}
        onChange={(event) => setEndDate(event.target.value)}
      />
    </div>
  );
}

export default DateRangePicker;
