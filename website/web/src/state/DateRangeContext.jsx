import { createContext, useContext, useMemo, useState } from 'react';

const DateRangeContext = createContext(null);

const formatDate = (value) => value.toISOString().slice(0, 10);

const getDefaultRange = () => {
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - 7);
  return {
    startDate: formatDate(start),
    endDate: formatDate(end),
  };
};

export function DateRangeProvider({ children }) {
  const [range, setRange] = useState(getDefaultRange);

  const value = useMemo(
    () => ({
      ...range,
      setStartDate: (startDate) => setRange((prev) => ({ ...prev, startDate })),
      setEndDate: (endDate) => setRange((prev) => ({ ...prev, endDate })),
      setRange,
    }),
    [range],
  );

  return <DateRangeContext.Provider value={value}>{children}</DateRangeContext.Provider>;
}

export function useDateRange() {
  const context = useContext(DateRangeContext);

  if (!context) {
    throw new Error('useDateRange must be used inside DateRangeProvider');
  }

  return context;
}
